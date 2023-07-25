import falcon
from falcon import Request, Response

from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker, Session

from ..util import pagination, require_auth, serialize
from ..response import ERROR_RESPONSE, GenericResponse

from ..database.models import User

from ..log import logging

import math
from uuid import UUID

class UserResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker):
        self.db_session = db_sessionmaker

    @falcon.before(require_auth)
    @falcon.before(pagination)
    def on_get(self, req: Request, resp: Response):
        try:
            page: int = req.context.page
            elements: int = req.context.elements

            with self.db_session() as db:
                users = db.scalars(select(User).offset((page - 1) * elements).limit(elements)).all()

                total_records: int = db.scalar(select(func.count()).select_from(User))

                resp.media = serialize(GenericResponse(value={
                    'totalPages': math.ceil(total_records / elements),
                    'data': users
                }))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)


    @falcon.before(require_auth)
    def on_get_by_id(self, req: Request, resp: Response, _id: UUID):
        try:
            with self.db_session() as db:
                result = db.execute(select(User).where(User.id == _id))
                user = result.scalar()

                if user is None:
                    resp.media = serialize(GenericResponse(value=None, errors=['No user with such id was found.']))
                    resp.status = falcon.HTTP_404
                    return

                resp.media = serialize(GenericResponse(value=user))
                resp.status = falcon.HTTP_200

        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)
