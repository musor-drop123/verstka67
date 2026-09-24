from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import router
import asyncpg
from limit import limiter
from contextlib import asynccontextmanager
import dotenv 
import os
dotenv.load_dotenv()
dsn = os.getenv("PG_DSN")
@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import create_tasks_db, create_users_db
    app.state.conn = await asyncpg.create_pool(dsn=dsn)
    await create_users_db(app.state.conn)
    await create_tasks_db(app.state.conn)
    yield 
    await app.state.conn.close()

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(router=router)
def get_db(request: Request):
    return request.app.state.conn
