import falcon
from falcon import Request, Response

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from ..util import pagination, require_auth, serialize

from ..database.models import User

from ..log import logging
from ..docs import spec

from ..validation import PaginationParams, PaginatedResponse, UserData, ErrorResponse
from ..validation import INTERNAL_ERROR_RESPONSE, ResponseWrapper

from spectree import Response as SpecResponse

import math
from uuid import UUID

class UserResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker):
        self.db_session = db_sessionmaker

    @spec.validate(
        query=PaginationParams,
        resp=SpecResponse(HTTP_200=ResponseWrapper, HTTP_500=ErrorResponse)
    )
    @falcon.before(require_auth)
    @falcon.before(pagination)
    def on_get(self, req: Request, resp: Response):
        try:
            page: int = req.context.page
            elements: int = req.context.elements

            with self.db_session() as db:
                users = db.scalars(select(User).offset((page - 1) * elements).limit(elements)).all()

                total_records: int = db.scalar(select(func.count()).select_from(User))

                resp.media = serialize(ResponseWrapper(
                    value=PaginatedResponse(
                        totalPages=math.ceil(total_records / elements),
                        data=users
                    )
                ))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(INTERNAL_ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)


    @spec.validate(
        resp=SpecResponse(HTTP_200=ResponseWrapper, HTTP_500=ErrorResponse),
        path_parameter_descriptions={
            '_id': 'A UUID that corresponds to a user.'
        }
    )
    @falcon.before(require_auth)
    def on_get_by_id(self, req: Request, resp: Response, _id: UUID):
        try:
            with self.db_session() as db:
                result = db.execute(select(User).where(User.id == _id))
                user = result.scalar()

                if user is None:
                    resp.media = serialize(ResponseWrapper(value=None, errors=['No user with such id was found.']))
                    resp.status = falcon.HTTP_404
                    return

                resp.media = serialize(ResponseWrapper(value=user))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(INTERNAL_ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)
