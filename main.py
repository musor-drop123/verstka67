from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
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
    app.state.conn = await asyncpg.connect(dsn=dsn)
    
    yield 
    await app.state.conn.close()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="static/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(router=router)
async def get_db(request: Request):
    return request.app.state.conn
