from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyCookie
from schemas import StudentLoginData, Token
import datetime
from services import create_access_token, create_refresh_token
import uuid
from db import create_users_db
cookie_sheme = APIKeyCookie()
router = APIRouter()
@router.get("/main")
async def main(request: Request):
    from main import templates
    return templates.TemplateResponse(request=request, name="item.html")
@router.get("/login")
async def login(data: StudentLoginData):
    from main import get_db
    id = uuid.uuid4()
    response = RedirectResponse(url="/main")
    access_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, exp=access_exp)
    payload_refresh = Token(id=id, exp=refresh_exp)
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax")
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax")
    db = get_db()
    
    return response

    
    