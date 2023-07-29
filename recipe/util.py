import falcon.asgi
from falcon.asgi import Request, Response

from uuid import UUID

import jwt
import os

from .database.models import Authority
from .validation import ResponseWrapper

class FieldsMissing(falcon.HTTPBadRequest):
    fields: list[str]

    def __init__(self, f: list[str]):
        self.fields = f

def require_fields(req: Request, resp: Response, resource, params, required: list[str], optional: list[str] = []):
    body = req.media
    req.context.body = {}

    for field in required:
        if field not in body:
            raise FieldsMissing(required)
        req.context.body[field] = body[field]

    for field in optional:
        req.context.body[field] = body[field] if (field in body) else None

def handle_fields_missing(req: Request, resp: Response, ex: FieldsMissing, params):
    resp.status = falcon.HTTP_400
    resp.media = {
        'value': None,
        'errors': [
            'The following fields are required: '
            + ''.join(['`' + f + '`, ' for f in ex.fields[:-1]])
            + '`' + ex.fields[-1] + '`.'
        ]
    }

class Unauthorized(falcon.HTTPForbidden):
    reason: str

    def __init__(self, reason: str):
        self.reason = reason

class AccessDenied(falcon.HTTPForbidden):
    reason: str

    def __init__(self, reason: str):
        self.reason = reason

def check_auth(req: Request, resp: Response, resource, params, allowed_authorities: int = Authority.USER | Authority.MODERATOR | Authority.ADMIN):
    auth_header: str | None = req.auth
    if auth_header is None:
        raise Unauthorized('use `Authorization` header to pass the authorization token')
    
    split = auth_header.split()
    if len(split) != 2 or split[0].lower() != 'bearer':
        raise Unauthorized('the format of `Authorization` header is invalid')

    token = split[1].strip()
    secret = os.environ.get('RECIPE_APP_SECRET')

    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise Unauthorized('the authorization token has expired. Please, authorize again')
    except Exception:
        raise Unauthorized('there was an error verifying the authorization token')

    if payload['role'] & allowed_authorities:
        req.context.user_id = UUID(payload['user_id'])
    else:
        raise AccessDenied('You are not allowed to perform this operation.')

def handle_unauthorized(req: Request, resp: Response, ex: Unauthorized, params):
    resp.status = falcon.HTTP_401
    resp.media = {
        'value': None,
        'errors': [
            'Authorization failed. Reason: ' + ex.reason + '.'
        ]
    }

def handle_access_denied(req: Request, resp: Response, ex: AccessDenied, params):
    resp.status = falcon.HTTP_403
    resp.media = {
        'value': None,
        'errors': [
            'Access denied. Reason: ' + ex.reason + '.'
        ]
    }

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 50

class PaginationError(falcon.HTTPBadRequest):
    msgs: list[str]

    def __init__(self, msg: list[str]):
        self.msgs = msg

def handle_pagination_error(req: Request, resp: Response, ex: PaginationError, params):
    resp.status = falcon.HTTP_400
    resp.media = {
        'value': None,
        'errors': ex.msgs
    }

def pagination(req: Request, resp: Response, resource, params):
    query_params = req.params

    if 'elements' not in query_params or 'page' not in query_params:
        req.context.elements = DEFAULT_PAGE_SIZE
        req.context.page = 1
    else:
        errors: list[str] = []
        try:
            elements = int(query_params['elements'])
        except Exception:
            errors.append('There was an error parsing the `elements` parameter.')
        
        try:
            page = int(query_params['page'])
        except Exception:
            errors.append('There was an error parsing the `page` parameter.')

        if elements < 1 or elements > MAX_PAGE_SIZE:
            errors.append(f'The `elements` parameter must be a positive integer, less than or equal to {MAX_PAGE_SIZE}')

        if page < 1:
            errors.append('The `page` parameter must be a positive integer.')

        if len(errors) > 0:
            raise PaginationError(errors)
        
        req.context.elements = elements
        req.context.page = page
