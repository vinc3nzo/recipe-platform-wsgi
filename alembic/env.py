from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from dotenv import load_dotenv
import os

load_dotenv()

db_password = os.environ.get('RECIPE_DATABASE_PASSWORD')
if db_password is None:
    raise Exception('Please, set the `RECIPE_DATABASE_PASSWORD` environment variable. You may use the `.env` file for your convenience.')

db_user = os.environ.get('RECIPE_DATABASE_USER', 'postgres')
db_name = os.environ.get('RECIPE_DATABASE_NAME', 'recipe-postgres')
db_host = os.environ.get('RECIPE_DATABASE_HOST', 'localhost')
db_port = os.environ.get('RECIPE_DATABASE_PORT', '5432')

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option(
    'sqlalchemy.url',
    f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# check if the database exists
from recipe.database.database import validate_db_presence
db_url = config.get_main_option('sqlalchemy.url')
validate_db_presence(db_url)

# add your model's MetaData object here
# for 'autogenerate' support

from recipe.database.models import OrmBase
target_metadata = OrmBase.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
