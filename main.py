from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from routers import router
import asyncpg
from contextlib import asynccontextmanager
import dotenv 
import os
dotenv.load_dotenv()
dsn = os.getenv("PG_DSN")
@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import create_tasks_db, create_users_db
    app.state.conn = await asyncpg.connect(dsn=dsn)
    await create_users_db(app.state.conn)
    await create_tasks_db(app.state.conn)
    yield 
    await app.state.conn.close()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router=router)
def get_db(request: Request):
    return request.app.state.conn
