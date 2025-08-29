import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import xxhash
from pydantic import BaseModel, EmailStr
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

import src.db as db

AUTH_JWT_SECRET: str | None = None
AUTH_JWT_ALGORITHM = "HS256"
AUTH_JWT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days by default


def init() -> None:
    global AUTH_JWT_SECRET
    AUTH_JWT_SECRET = os.getenv("AUTH_JWT_SECRET")
    assert AUTH_JWT_SECRET is not None, "Set AUTH_JWT_SECRET in .env"
    logging.info("Auth initialised: JWT-based email login enabled")


class TokenPayload(BaseModel):
    sub: str  # uid
    email: EmailStr
    iat: int
    exp: int


def normalise_email(email: str) -> str:
    return email.strip().lower()


def hash_email(email: str) -> str:  # ! NOT cryptographically secure
    return xxhash.xxh3_128_hexdigest(email.encode("utf-8"))


async def issue_token_for_email(email: str, session: AsyncSession) -> str:
    """Create or get a user by email and return a signed JWT (sub=uid)."""
    assert AUTH_JWT_SECRET is not None, "Auth not initialised"
    email = normalise_email(email)
    email_hash = hash_email(email)

    result = await session.exec(select(db.User).where(db.User.id == email_hash))
    user = result.first()
    if user is None:
        logging.info(f"DB: Creating new user: email={email}, uid={email_hash}")
        user = db.User(id=email_hash, email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        logging.info(f"DB: User exists (UID): email={email}, uid={email_hash}")

    now = datetime.now(UTC)
    payload = TokenPayload(
        sub=user.id,
        email=user.email,
        iat=int(now.timestamp()),
        exp=int((now + timedelta(seconds=AUTH_JWT_TTL_SECONDS)).timestamp()),
    )
    token = jwt.encode(payload.dict(), AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALGORITHM)
    return token


async def get_or_create_user(id_token: str, session: AsyncSession) -> db.User:
    """Verify JWT, and ensure a corresponding user exists (email as ID)."""
    assert AUTH_JWT_SECRET is not None, "Auth not initialised"

    try:
        decoded: dict[str, Any] = jwt.decode(
            id_token,
            AUTH_JWT_SECRET,
            algorithms=[AUTH_JWT_ALGORITHM],
        )
        uid = str(decoded.get("sub"))

        if not uid:
            raise ValueError("Invalid token: missing sub (uid)")

        user = await session.get(db.User, uid)
        if user:
            logging.info(f"DB: User exists: {uid}")
            return user

        raise ValueError("User not found")

    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token expired") from exc

    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e
