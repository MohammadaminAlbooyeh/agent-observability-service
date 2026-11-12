"""Initialize the database schema by creating all SQLAlchemy tables."""

import asyncio

from src.database.base import engine, Base


async def main() -> None:
    """Create all database tables defined on the SQLAlchemy Base metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
