import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context
from src.db import Episode, EpisodeStatus, Game, Transition, User  # noqa: F401

load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# if (
#     (CONNECTION_NAME := os.getenv("GCP_SQL_CONNECTION_NAME"))
#     and (DB_USER := os.getenv("GCP_SQL_USER"))
#     and (DB_PASS := os.getenv("GCP_SQL_PASSWORD"))
#     and (DB_NAME := os.getenv("GCP_SQL_NAME"))
# ):
#     DB_DRIVER = "psycopg2"
#     DB_PATH = f"postgresql+{DB_DRIVER}://{DB_USER}:{DB_PASS}@localhost:1234/{DB_NAME}"
# else:  # local
#     sqlite_file_name = "db.db"
#     DB_PATH = f"sqlite:///{sqlite_file_name}"
sqlite_file_name = "tmp/db.db"
# Ensure directory exists for local SQLite database
os.makedirs(os.path.dirname(sqlite_file_name), exist_ok=True)
DB_PATH = f"sqlite:///{sqlite_file_name}"

config.set_main_option("sqlalchemy.url", DB_PATH)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

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
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
