from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from collections.abc import Generator, AsyncGenerator

from app.database import SessionLocal, async_session_maker


def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
