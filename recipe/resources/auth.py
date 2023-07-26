import falcon
from falcon import Request, Response

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

from ..util import serialize
from ..database.models import User, UserPassword, Authority
from ..spec import api
from ..validation import (
    UserPasswordCreate, UserCreate, ResponseWrapper, INTERNAL_ERROR_RESPONSE,
    LoginRequest, ErrorResponse, RegistrationRequest
)
from ..security import authorize_user
from ..log import logging

import bcrypt

from spectree import Response as SpecResponse

class AuthResource:

    db_session: sessionmaker[Session]

    def __init__(self, db_sessionmaker: sessionmaker[Session]):
        self.db_session = db_sessionmaker

    @api.validate(
        resp=SpecResponse(
            HTTP_200=(ResponseWrapper, 'login successful'),
            HTTP_401=(ErrorResponse, 'credentials are incorrect'),
            HTTP_404=(ErrorResponse, 'user not found'),
            HTTP_500=ErrorResponse
        ),
        json=LoginRequest,
        security={}
    )
    def on_post_login(self, req: Request, resp: Response):
        try:
            username: str = req.context.json.username
            password: str = req.context.json.password

            with self.db_session() as db:
                user = db.execute(select(User).where(User.username == username)).scalar()
                if user is None:
                    resp.media = {
                        'value': None,
                        'errors': ['No user with such username was found.']
                    }
                    resp.status = falcon.HTTP_404
                    return
                
                user_password = db.execute(select(UserPassword).where(UserPassword.user_id == user.id)).scalar()

                if not bcrypt.checkpw(password.encode('utf-8'), user_password.hashed_password):
                    resp.media = resp.media = {
                        'value': None,
                        'errors': ['The password is incorrect.']
                    }
                    resp.status = falcon.HTTP_401
                    return
            
                token = authorize_user(user.id, user.role)

                resp.media = {
                    'value': { 'token': token },
                    'errors': None
                }
                resp.status = falcon.HTTP_200
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)
    
    @api.validate(
        resp=SpecResponse(
            HTTP_200=(ErrorResponse, 'username is already taken'),
            HTTP_201=(ResponseWrapper, 'user successfully registered'),
            HTTP_500=ErrorResponse
        ),
        json=RegistrationRequest,
        security={}
    )
    def on_post_register(self, req: Request, resp: Response):
        try:
            username: str = req.context.json.username
            password: str = req.context.json.password
            first_name: str = req.context.json.first_name
            last_name: str = req.context.json.last_name

            with self.db_session() as db:
                user = db.execute(select(User).where(User.username == username)).scalar()
                if user is not None:
                    resp.media = {
                        'value': None,
                        'errors': ['This username is already taken.']
                    }
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

                resp.media = {
                    'value': None,
                    'errors': None
                }
                resp.status = falcon.HTTP_201
        except Exception as e:
            resp.media = INTERNAL_ERROR_RESPONSE
            resp.status = falcon.HTTP_500
            logging.exception(e)

        