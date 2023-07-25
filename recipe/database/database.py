from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy_utils import create_database, database_exists

from .models import OrmBase

def new_engine(url: str) -> Engine:
    return create_engine(
        url,
        connect_args={'check_same_thread': False}
    )

def new_sessionmaker(engine: Engine):
    return sessionmaker(engine)

def init_db(engine: Engine):
    # Not used. Using alembic migrations instead
    OrmBase.metadata.create_all(engine)

def validate_db_presence(url: str):
    if not database_exists(url):
        create_database(url)