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


async def init() -> None:
    global engine, connector
    if (
        (connection_name := os.getenv("GCP_SQL_CONNECTION_NAME"))
        and (db_user := os.getenv("GCP_SQL_USER"))
        and (db_pass := os.getenv("GCP_SQL_PASSWORD"))
        and (db_name := os.getenv("GCP_SQL_NAME"))
    ):
        db_driver = "asyncpg"

        connector = await create_async_connector()

        async def getconn() -> asyncpg.Connection:
            if connector is None:
                raise RuntimeError("Connector is not initialized.")

            conn = await connector.connect_async(
                instance_connection_string=connection_name,
                driver=db_driver,
                user=db_user,
                password=db_pass,
                db=db_name,
            )
            return conn

        engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=getconn,
            echo=False,
        )

    else:  # local
        sqlite_file_name = "db.db"
        connection_name = f"sqlite+aiosqlite:///{sqlite_file_name}"
        engine = create_async_engine(
            connection_name,
            echo=True,
        )


class User(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
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

    episodes: list["Episode"] = Relationship(back_populates="user")


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
    user_id: str = Field(foreign_key="user.id", index=True)
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

    user: User = Relationship(back_populates="episodes")
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
    time_obs_shown: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    time_action_input: datetime = Field(sa_column=Column(DateTime(timezone=True)))

    episode: Episode = Relationship(back_populates="transitions")
