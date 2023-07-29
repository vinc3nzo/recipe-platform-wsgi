from uuid import UUID, uuid4
from datetime import datetime, timedelta

import jwt
import os

from .database.models import Authority

BEARER_TOKEN_EXPIRATION_TIME: int = 60 * 60 * 24 * 30 # sec

def get_admin_token() -> str:
    payload = {
        'user_id': str(uuid4()),
        'role': Authority.ADMIN | Authority.MODERATOR | Authority.USER,
        'exp': datetime.utcnow() + timedelta(seconds=BEARER_TOKEN_EXPIRATION_TIME)
    }

    secret: str = os.environ.get('RECIPE_APP_SECRET')
    token: str = jwt.encode(payload, secret, algorithm="HS256")

    return token

def authorize_user(id: UUID, role: int) -> str:
    payload = {
        'user_id': str(id),
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=BEARER_TOKEN_EXPIRATION_TIME)
    }

    secret: str = os.environ.get('RECIPE_APP_SECRET')
    token: str = jwt.encode(payload, secret, algorithm="HS256")

    return token