import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel.ext.asyncio.session import AsyncSession

import src.auth as auth
import src.db as db
from src.game import Game, game_loop
from src.uploader import Uploader


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s\n",
    )
    await db.init()
    auth.init()
    app.state.uploader = Uploader(db.engine)

    # initialisation above
    yield  # app running
    # cleanup below

    await app.state.uploader.close()
    if db.connector:
        await db.connector.close_async()


app = FastAPI(lifespan=lifespan)


# Enable CORS so the frontend (served from Firebase or elsewhere) can call the API
# In production you may want to restrict the allowed origins instead of "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Replace with specific origins for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


GAME_CONFIGS_PATH = Path("src/configs")


@app.get("/games")
def list_games() -> list[dict[str, str]]:
    game_info = []
    for config_path in GAME_CONFIGS_PATH.glob("*.yaml"):
        with open(config_path) as f:
            config = yaml.safe_load(f)
        game_info.append(
            {
                "id": config_path.stem,
                "display_name": config["display_name"],
            }
        )
    return game_info


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    from_public_website: bool,
    token: str | None = None,
) -> None:
    """Handle a new WebSocket connection, creating as unique game for it."""

    if not token:
        logging.error("WS: No token provided.")
        await websocket.close(code=1008)  # Policy Violation
        return

    async with AsyncSession(
        db.engine,
    ) as session:
        user: db.User | None = await auth.get_or_create_user(token, session)
        if not user:
            logging.error(f"WS: Invalid token: {token}")
            await websocket.close(code=1008)  # Policy Violation
            return

    game_config_path = GAME_CONFIGS_PATH / f"{game_id}.yaml"
    assert game_config_path.is_file(), f"Game config {game_config_path} not found"

    with open(game_config_path) as f:
        game_config = yaml.safe_load(f)
    seed = int(datetime.now(UTC).timestamp() * 1000)
    game = Game(seed, **game_config)

    db_game: db.Game = None
    async with AsyncSession(
        db.engine,
        expire_on_commit=False,
    ) as session:
        existing_db_game = await session.get(db.Game, game_id)
        if not existing_db_game:
            db_game = db.Game(
                id=game_id,
                config=game_config,
            )
            session.add(db_game)
            await session.commit()
            db_game = db_game
            logging.info(f"DB: Game created: {game_id}")
        else:
            db_game = existing_db_game
            logging.info(f"DB: Game exists: {game_id}")

    await websocket.accept()

    try:
        # Send setup material
        initial_state = game.get_init_state()
        await websocket.send_text(json.dumps(initial_state))

        db_episode: db.Episode
        async with AsyncSession(
            db.engine,
            expire_on_commit=False,
        ) as session:
            db_episode = db.Episode(
                user_id=user.id,
                game_id=db_game.id,
                seed=seed,
                from_public_website=from_public_website,
            )
            session.add(db_episode)
            await session.commit()
            db_episode = db_episode
            logging.info(f"DB: Episode created: {db_episode.id}")

        # Start the game loop for this client, using the global uploader
        game_loop_task = asyncio.create_task(
            game_loop(
                websocket,
                game,
                app.state.uploader,
                db_episode.id,
            )
        )
        await game_loop_task

    except WebSocketDisconnect:
        logging.info("WS: Client forcefully disconnected.")

    finally:
        assert db_episode, f"db_episode lost; currently: {db_episode}"

        db_episode.n_steps = game.n_steps
        if game.won:
            db_episode.status = db.EpisodeStatus.WON
        elif game.game_over:
            db_episode.status = db.EpisodeStatus.LOST
        # else remains as default db.EpisodeStatus.INCOMPLETE

        async with AsyncSession(
            db.engine,
            expire_on_commit=False,
        ) as session:
            session.add(db_episode)
            await session.commit()
            logging.info(
                f"DB: Episode updated: {db_episode}; n_steps: {db_episode.n_steps}; final status: {db_episode.status}"
            )

        if game_loop_task:
            game_loop_task.cancel()
        game.env.close()
        logging.info("WS: Game loop task cancelled and environment closed.")
