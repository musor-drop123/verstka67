import logging

from fastapi import APIRouter, HTTPException, Request, Depends, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.responses import RedirectResponse, Response
from fastapi.security import APIKeyCookie
import httpx
from replicate.client import Client
from schemas import AiSchema, StudentSignUpData, Task, TeacherLoginData, Token, LogInUser
import datetime
from services import create_access_token, create_refresh_token, decode_refresh_token, hash_pw, check_pw, decode_access_token, admin_code, proxy_url
import uuid, jwt
from db import create_user, create_task, get_task_by_id, get_tasks_by_number, get_user_by_id, get_user_by_name
access_cookie_sheme = APIKeyCookie(name="access_token")
refresh_cookie_sheme = APIKeyCookie(name="refresh_token")
async def get_admin(token=Depends(access_cookie_sheme)):
    try:
        decoded = await decode_access_token(token)
        if decoded["is_admin"] != "True":
            raise HTTPException(status_code=403)
        return decoded["id"]
    except jwt.ExpiredSignatureError:
        # Токен истек по времени (истек `exp` claim)
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
async def get_user(token=Depends(access_cookie_sheme)):
    try:
        decoded = await decode_access_token(token)
        return decoded["id"]
    except jwt.ExpiredSignatureError:
        # Токен истек по времени (истек `exp` claim)
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
async def get_refresh_user(token=Depends(refresh_cookie_sheme)):
    try:
        decoded = await decode_refresh_token(token)
        return decoded["id"]
    except jwt.ExpiredSignatureError:
        # Токен истек по времени (истек `exp` claim)
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    
router = APIRouter()

@router.get("/signup")
async def signup(data: StudentSignUpData, request: Request):
    from main import get_db
    id = str(uuid.uuid4())
    response = RedirectResponse(url="/main")
    access_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, exp=access_exp).model_dump()
    payload_refresh = Token(id=id, exp=refresh_exp).model_dump()
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    db = get_db(request)
    password= hash_pw(data.password)
    await create_user(db, id, data.name, data.surname, password, "False")
    return response
@router.get("/profile")
async def get_profile(request: Request, user_id=Depends(get_user)):
    from main import get_db
    db = get_db(request)
    user_data = get_user_by_id(db, str(user_id))
    return user_data
@router.get("/refresh")
async def refresh(user_id=Depends(refresh_cookie_sheme)):
    response = RedirectResponse("/main")
    access_token = await create_access_token(user_id)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    return response
@router.post("/login")
async def login(data: LogInUser, request: Request):
    from main import get_db
    db = get_db(request)
    user_data = await get_user_by_name(db, data.name)
    if not check_pw(data.password, user_data["password"]):
        return RedirectResponse("/signup")
    response = RedirectResponse("/main")
    id = user_data["id"]
    access_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, exp=access_exp).model_dump()
    payload_refresh = Token(id=id, exp=refresh_exp).model_dump()
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    return response
@router.post("/signup/admin")
async def admin_signup(data: TeacherLoginData, request: Request):
    from main import get_db
    if data.admin_code != admin_code:
        raise HTTPException(status_code=401)
    id = str(uuid.uuid4())
    response = RedirectResponse(url="/admin/main")
    access_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, exp=access_exp).model_dump()
    payload_refresh = Token(id=id, exp=refresh_exp).model_dump()
    payload_access["is_admin"] = "True"
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    db = get_db(request)
    password= hash_pw(data.password)
    await create_user(db, id, data.name, data.surname, password, "True")
    return response

@router.post("/login/admin")
async def login(data: LogInUser, request: Request):
    from main import get_db
    db = get_db(request)
    user_data = await get_user_by_name(db, data.name)
    if not check_pw(data.password, user_data["password"]):
        return RedirectResponse("/signup")
    response = RedirectResponse("/admin/main")
    id = user_data["id"]
    access_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, exp=access_exp)
    payload_refresh = Token(id=id, exp=refresh_exp)
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    return response
@router.post("/admin/add_task")
async def add_task(data: Task, request: Request, user_id=Depends(get_admin)):
    from main import get_db
    db = get_db(request)
    id = str(uuid.uuid4())
    await create_task(db, id, data.name,data.number, data.diff, data.text, data.answer, data.description)
    return {"status": "successful"}
@router.get("/main/tasks/{id}")
async def get_task(id, request: Request, user=Depends(get_user)):
    from main import get_db
    db = get_db(request)
    task = await get_task_by_id(db, id)
    return task 
@router.get("main/tasks")
async def get_task(number, request: Request, user=Depends(get_user)):
    from main import get_db
    db = get_db(request)
    data = await get_tasks_by_number(db, number)
    return data
async def get_ws_user(ws: WebSocket):
    token = ws.cookies.get("access_token")
    if not token:
        raise WebSocketException(code=1008)
    try:
        decoded_token = await decode_access_token(token)
        return decoded_token["id"]
    except:
        raise WebSocketException(code=1008)
@router.websocket("/ws/explain/ai")
async def explain_task(ws: WebSocket, user_id=Depends(get_ws_user)):
    await ws.accept()
    try: 
        while True:
            data = ws.receive_json()
            input = {
                "system_prompt": "Тебе на вход подаются: условие задачи, код ученика (может быть пустым) и комментарий ученика. Тебе нужно ответить на вопросы ученика и помочь ему с решением (решать полностью задачу нельзя, только подсказки и обьяснения). Если запрос ученика не связан с информатикой, то отвечай, что ты можешь помочь только с информатикой. Также твой ответ не должен быть длиннее 500 символов",
                "prompt": f"Условие задачи: {data["task"]} Код ученика: {data["code"]} Комментарий ученика: {data["comment"]}",
                "max_tokens": 500
            }
            transport = httpx.HTTPTransport(proxy=httpx.Proxy(url=proxy_url))
            client = Client(transport=transport)
            
            for event in client.stream("qwen/qwen3-7-plus", input=input):
                await ws.send_text(event)
    except WebSocketDisconnect:
        logging.debug("websocket connection closed")



