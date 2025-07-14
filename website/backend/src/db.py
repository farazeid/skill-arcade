import asyncio
import enum
import os
import uuid
from datetime import UTC, datetime

import asyncpg
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector, create_async_connector
from sqlalchemy import BigInteger, DateTime
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import JSON, Column, Enum, Field, Relationship, SQLModel

load_dotenv()

connector: Connector | None = None
engine: AsyncEngine


# class User(SQLModel, table=True):
#     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
#     email: str = Field(unique=True, index=True)
#     password_hash: str
#     password_salt: str
#     date_of_birth: datetime | None = Field(default=None)
#     time_created: datetime = Field(
#         default_factory=lambda: datetime.now(UTC),
#         sa_column_kwargs={"onupdate": datetime.now(UTC)},
#     )
#     time_updated: datetime = Field(
#         default_factory=lambda: datetime.now(UTC),
#         sa_column_kwargs={"onupdate": datetime.now(UTC)},
#     )

#     episodes: list["Episode"] = Relationship(back_populates="user")


class Game(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    config: dict = Field(sa_column=Column(JSON))
    time_created: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=datetime.now(UTC),
        ),
    )

    episodes: list["Episode"] = Relationship(back_populates="game")


class EpisodeStatus(str, enum.Enum):
    INCOMPLETE = "incomplete"
    WON = "won"
    LOST = "lost"


class Episode(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    # user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    game_id: str = Field(foreign_key="game.id", index=True)
    seed: int = Field(sa_column=Column(BigInteger))
    n_steps: int | None = Field(default=None)
    status: EpisodeStatus = Field(
        sa_column=Column(Enum(EpisodeStatus)),
        default=EpisodeStatus.INCOMPLETE,
    )
    time_created: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=datetime.now(UTC),
        ),
    )
    time_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=datetime.now(UTC),
        ),
    )

    # user: User = Relationship(back_populates="episodes")
    game: Game = Relationship(back_populates="episodes")
    transitions: list["Transition"] = Relationship(back_populates="episode")


class Transition(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    episode_id: uuid.UUID = Field(foreign_key="episode.id", index=True)
    step: int
    obs_key: str | None = Field(default=None)
    action: int
    reward: float
    next_obs_key: str | None = Field(default=None)
    terminated: bool
    truncated: bool
    info: dict = Field(sa_column=Column(JSON))
    time_created: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )

    episode: Episode = Relationship(back_populates="transitions")


async def init():
    global engine, connector
    if (
        (CONNECTION_NAME := os.getenv("GCP_SQL_CONNECTION_NAME"))
        and (DB_USER := os.getenv("GCP_SQL_USER"))
        and (DB_PASS := os.getenv("GCP_SQL_PASSWORD"))
        and (DB_NAME := os.getenv("GCP_SQL_NAME"))
    ):
        DB_DRIVER = "asyncpg"

        connector = await create_async_connector()

        async def getconn() -> asyncpg.Connection:
            conn = await connector.connect_async(
                CONNECTION_NAME,
                DB_DRIVER,
                user=DB_USER,
                password=DB_PASS,
                db=DB_NAME,
            )
            return conn

        engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=getconn,
            echo=False,
        )

    else:  # local
        sqlite_file_name = "db.db"
        CONNECTION_NAME = f"sqlite+aiosqlite:///{sqlite_file_name}"
        engine = create_async_engine(
            CONNECTION_NAME,
            echo=True,
        )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
