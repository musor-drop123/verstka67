from asyncpg import Pool
async def create_users_db(db: Pool):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            user_name TEXT UNIQUE,
            name TEXT,
            password TEXT,
            is_admin TEXT
        );
    """)
async def create_tasks_db(db: Pool):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks(
            id TEXT PRIMARY KEY,
            name TEXT,
            number TEXT,
            diff TEXT,
            text TEXT,
            answer TEXT,
            description TEXT
        );
    """)
async def get_user_by_id(db: Pool, id):
    data = await db.fetchrow("""
        SELECT * FROM users WHERE id = $1;
    """, id)
    data = dict(data)
    del data["password"]
    return data 
async def get_user_by_name(db: Pool, name):
    data = await db.fetchrow("""
        SELECT * FROM users WHERE name = $1;
    """, name)
    data = dict(data)
    return data 
async def get_task_by_id(db: Pool, id):
    data = await db.fetchrow("""
            SELECT * FROM tasks WHERE id = $1;
        """, str(id))
    data = dict(data)
    return data 
async def get_answer_by_id(db: Pool, id):
    data = await db.fetchrow("""
            SELECT answer FROM tasks WHERE id = $1;
        """, str(id))
    data = dict(data)
    return data 
async def get_tasks_by_number(db: Pool, number):
    data = await db.fetchrow("""
            SELECT * FROM tasks WHERE number = $1 ORDER BY random() LIMIT 1;
        """, str(number))
    data = dict(data)
    return data
async def create_user(db: Pool, id,user_name ,name ,password ,is_admin ):
    await db.execute("""INSERT INTO users VALUES ($1, $2, $3, $4, $5);""", id,user_name ,name ,password ,is_admin )
async def create_task(db: Pool, id, name, number, diff, text, answer, description):
    await db.execute("""INSERT INTO tasks VALUES ($1, $2, $3, $4, $5, $6, $7)""", id, name, number, diff, text, answer, description)