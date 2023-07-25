from datetime import datetime

import falcon.asgi
from falcon.asgi import Request, Response

from uuid import UUID

import jwt
import os

from .database.models import Authority
from .response import GenericResponse

def serialize(obj: object) -> list | dict[str, dict | list | str | int | float | None]:
    """Convert any complex Python object into its
    hopefully JSON-serializable, dictionary form.
    
    If the `obj` or one of its fields and subfields has a method
    named `serialize()`, then it will be called.
    
    Cyclic references will cause the function to enter an
    infinite loop. Use with caution."""

    if getattr(obj, 'serialize', False):
        return obj.serialize() # if the `obj` has `serialize()` method, invoke it

    if isinstance(obj, UUID):
        return str(obj)

    if isinstance(obj, (list, tuple)):
        return [serialize(e) for e in obj] # collections are returned as lists

    if isinstance(obj, (str, int, float)):
        return obj # primitive types are returned as-is
    
    if isinstance(obj, datetime):
        return obj.timestamp() # serialize time as Unix timestamp

    if isinstance(obj, dict):
        d = obj
    else:
        d = obj.__dict__

    res = {}
    for k in d:
        if not k.startswith('_'):
            if d[k] is None:
                res[k] = None
            else:
                res[k] = serialize(d[k])
    return res

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
    resp.media = serialize(GenericResponse(
        value=None,
        errors=[
            'The following fields are required: '
            + ''.join(['`' + f + '`, ' for f in ex.fields[:-1]])
            + '`' + ex.fields[-1] + '`.'
        ]
    ))

class AccessDenied(falcon.HTTPForbidden):
    reason: str

    def __init__(self, reason: str):
        self.reason = reason

def require_auth(req: Request, resp: Response, resource, params, allowed_authorities: int = Authority.USER):
    key_header: str | None = req.get_header('X-Auth-Token')
    if key_header is None:
        raise AccessDenied('use the `X-Auth-Token` header to pass the authorization token')
    
    if len(key_header.split()) != 1:
        raise AccessDenied('the format of `X-Auth-Token` header is invalid')

    token = key_header.strip()
    secret = os.environ.get('APP_SECRET')

    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise AccessDenied('the authorization token has expired. Please, authorize again')
    except Exception:
        raise AccessDenied('there was an error verifying the authorization token')
    
    if payload['role'] & allowed_authorities:
        req.context.user_id = UUID(payload['user_id'])
    else:
        raise AccessDenied('you are not allowed to perform this operation')

def handle_access_denied(req: Request, resp: Response, ex: AccessDenied, params):
    resp.status = falcon.HTTP_403
    resp.media = serialize(GenericResponse(
        value=None,
        errors=[
            'Authorization failed. Reason: ' + ex.reason + '.'
        ]
    ))

DEFAULT_PAGE_SIZE: int = 20

class PaginationError(falcon.HTTPBadRequest):
    msgs: list[str]

    def __init__(self, msg: list[str]):
        self.msgs = msg

def handle_pagination_error(req: Request, resp: Response, ex: PaginationError, params):
    resp.status = falcon.HTTP_400
    resp.media = serialize(GenericResponse(
        value=None,
        errors=ex.msgs
    ))

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

        if elements < 1:
            errors.append('The `elements` parameter must be a positive integer.')

        if page < 1:
            errors.append('The `page` parameter must be a positive integer.')

        if len(errors) > 0:
            raise PaginationError(errors)
        
        req.context.elements = elements
        req.context.page = page
