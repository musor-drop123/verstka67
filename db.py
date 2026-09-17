from asyncpg import Connection
async def create_users_db(db: Connection) :
    await db.execute("""
        CREATE TABLE users IF NOT EXISTS (
            id TEXT PRIMARY KEY,
            name TEXT,
            surname TEXT,
            password TEXT
            grade TEXT
        );
    """)
async def create_tasks_db(db: Connection):
    await db.execute("""
        CREATE TABLE tasks IF NOT EXISTS (
            id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            user_id TEXT REFERENCES users(id)
        )
    """)