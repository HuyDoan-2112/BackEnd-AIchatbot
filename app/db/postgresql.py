from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker
from typing import AsyncGenerator, Optional

class PostgreSQLConnection:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.SessionLocal: Optional[async_sessionmaker[AsyncSession]] = None
        
    async def connect(self):
        """Initialize the database engine and session factory"""
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        self.SessionLocal = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a session (FastAPI dependency-style)."""
        if self.SessionLocal is None:
            await self.connect()
        async with self.SessionLocal() as session:
            yield session
    
    async def close(self):
        """Close the database connection"""
        if self.engine:
            await self.engine.dispose()


db_connection: Optional[PostgreSQLConnection] = None

def get_db_connection() -> PostgreSQLConnection:
    assert db_connection is not None, "db_connection not initialized"
    return db_connection