import os
import pytest

from sqlalchemy import Engine, create_engine

from recipe.database.database import init_db

def pytest_sessionstart(session):
    db_url = 'sqlite:///db/test.db'

    if not os.path.exists('./db/test.db'):
        engine = create_engine(db_url)
        init_db(engine)

def pytest_sessionfinish(session):
    if os.path.exists('./db/test.db'):
        os.remove('./db/test.db')

def pytest_configure():
    pytest.user_token = None
    pytest.recipe_id = None
    pytest.user_id = None