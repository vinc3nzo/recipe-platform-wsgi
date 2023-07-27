import falcon
from falcon import Request, Response

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from ..util import check_auth, serialize

from ..database.models import User

from ..log import logging
from ..spec import api

from ..validation import (
    PaginationParams, PaginatedUserResponse,
    UserResponse, ErrorResponse
)
from ..validation import INTERNAL_ERROR_RESPONSE

from spectree import Response as SpecResponse

import math
from uuid import UUID

class UserResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker):
        self.db_session = db_sessionmaker

    @api.validate(
        query=PaginationParams,
        resp=SpecResponse(
            HTTP_200=PaginatedUserResponse,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_500=ErrorResponse
        )
    )
    @falcon.before(check_auth)
    def on_get(self, req: Request, resp: Response):
        try:
            page: int = req.context.query.page
            elements: int = req.context.query.elements

            with self.db_session() as db:
                users = db.scalars(select(User).offset((page - 1) * elements).limit(elements)).all()

                total_records: int = db.scalar(select(func.count()).select_from(User))

                resp.media = {
                    'value': {
                        'totalPages': math.ceil(total_records / elements),
                        'data': [
                            user.serialize() for user in users
                        ]
                    }
                }
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)


    @api.validate(
        resp=SpecResponse(
            HTTP_200=UserResponse,
            HTTP_401=ErrorResponse,
            HTTP_403=ErrorResponse,
            HTTP_404=ErrorResponse,
            HTTP_500=ErrorResponse
        ),
        path_parameter_descriptions={
            '_id': 'A UUID that corresponds to a user.'
        }
    )
    @falcon.before(check_auth)
    def on_get_by_id(self, req: Request, resp: Response, _id: UUID):
        try:
            with self.db_session() as db:
                result = db.execute(select(User).where(User.id == _id))
                user = result.scalar()

                if user is None:
                    resp.media = {
                        'value': None,
                        'errors': ['No user with such id was found.']
                    }
                    resp.status = falcon.HTTP_404
                    return

                resp.media = {
                    'value': user.serialize(),
                    'errors': None
                }
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)
