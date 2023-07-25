import falcon
from falcon import Request, Response

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

from ..util import require_fields, serialize
from ..response import GenericResponse, ERROR_RESPONSE
from ..database.models import User, UserPassword, Authority
from ..database.validation import UserPasswordCreate, UserCreate
from ..security import authorize_user
from ..log import logging

import bcrypt

class AuthResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session]):
        self.db_session = db_sessionmaker

    @falcon.before(require_fields, ['username', 'password'])
    def on_post_login(self, req: Request, resp: Response):
        try:
            username: str = req.context.body['username']
            password: str = req.context.body['password']

            with self.db_session() as db:
                user = db.execute(select(User).where(User.username == username)).scalar()
                if user is None:
                    resp.media = serialize(GenericResponse(value=None, errors=['No user with such username was found.']))
                    resp.status = falcon.HTTP_404
                    return
                
                user_password = db.execute(select(UserPassword).where(UserPassword.user_id == user.id)).scalar()

                if not bcrypt.checkpw(password.encode('utf-8'), user_password.hashed_password):
                    resp.media = serialize(GenericResponse(value=None, errors=['The password is incorrect.']))
                    resp.status = falcon.HTTP_403
                    return
            
                token = authorize_user(user.id, user.role)

                resp.media = serialize(GenericResponse(value={'token': token}))
                resp.status = falcon.HTTP_200
        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)
    

    @falcon.before(require_fields, ['username', 'password', 'first_name', 'last_name'])
    def on_post_register(self, req: Request, resp: Response):
        try:
            username: str = req.context.body['username']
            password: str = req.context.body['password']
            first_name: str = req.context.body['first_name']
            last_name: str = req.context.body['last_name']

            with self.db_session() as db:
                user = db.execute(select(User).where(User.username == username)).scalar()
                if user is not None:
                    resp.media = serialize(GenericResponse(value=None, errors=['This username is already taken.']))
                    resp.status = falcon.HTTP_200
                    return
                
                c = UserCreate(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role=Authority.USER
                )

                new_user = User(c)
                db.add(new_user)
                db.commit()
                db.refresh(new_user)

                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

                new_user_id = new_user.id

                c = UserPasswordCreate(
                    user_id=new_user_id,
                    hashed_password=hashed
                )

                user_password = UserPassword(c)

                db.add(user_password)
                db.commit()

                resp.media = serialize(GenericResponse(value=None))
                resp.status = falcon.HTTP_201
        except Exception as e:
            resp.media = serialize(ERROR_RESPONSE)
            resp.status = falcon.HTTP_500
            logging.exception(e)

        