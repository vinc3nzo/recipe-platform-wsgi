from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker

from .models import OrmBase

def new_engine(url: str) -> Engine:
    return create_engine(
        url,
        connect_args={'check_same_thread': False}
    )

def new_sessionmaker(engine: Engine):
    return sessionmaker(engine)

def init_db(engine: Engine):
    OrmBase.metadata.create_all(engine) # TODO: replace with Alembic migration initialization