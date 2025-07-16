import json
import logging
import os
import sys

import firebase_admin
from firebase_admin import auth, credentials
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db as db


def init() -> None:
    """Initialise the auth module."""
    assert (firebase_json_raw := os.getenv("FIREBASE_CREDENTIALS")), "FIREBASE_CREDENTIALS environment variable must be set"  # fmt: skip

    firebase_json = json.loads(firebase_json_raw)
    try:
        cred = credentials.Certificate(firebase_json)
        firebase_admin.initialize_app(cred)
        logging.info("Firebase Admin SDK initialized successfully from local file.")

    except Exception as e:
        logging.error(f"Error initializing Firebase Admin SDK: {e}")
        sys.exit("Failed initialisation of Firebase Admin SDK")


async def get_or_create_user(id_token: str, session: AsyncSession) -> db.User | None:
    """Get a user from the database, creating it if it doesn't exist."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        user = await session.get(db.User, uid)
        if user:
            logging.info(f"DB: User exists: {uid}")
            return user

        logging.info(f"DB: Creating new user: {uid}")
        user = db.User(id=uid)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    except auth.InvalidIdTokenError:
        logging.error("Invalid ID token")
        return None

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None
