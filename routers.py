import asyncio
import logging
import os
import dotenv
import aiofiles
from limit import limiter
dotenv.load_dotenv()
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.responses import RedirectResponse, Response
from fastapi.security import APIKeyCookie
import httpx
from replicate.client import Client
from schemas import StudentSignUpData, Task, TeacherLoginData, Token, LogInUser
import datetime
from services import create_access_token, create_refresh_token, decode_refresh_token, hash_pw, check_pw, decode_access_token, admin_code, proxy_url
import uuid, jwt
from db import create_user, create_task, get_answer_by_id, get_task_by_id, get_tasks_by_number, get_user_by_id, get_user_by_name
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
@limiter.limit("5/minute")
@router.post("/signup")
async def signup(data: StudentSignUpData, request: Request, response: Response):
    from main import get_db
    id = str(uuid.uuid4())
    access_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, is_admin="False", exp=access_exp).model_dump()
    payload_refresh = Token(id=id, is_admin="False", exp=refresh_exp).model_dump()
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    db = get_db(request)
    password = await asyncio.to_thread(hash_pw, data.password)
    await create_user(db, id, data.user_name, data.name, password.decode(), "False")
    return {"status": "successful"}
@limiter.limit("5/minute")
@router.get("/profile")
async def get_profile(request: Request, user_id=Depends(get_user)):
    from main import get_db
    db = get_db(request)
    user_data = await get_user_by_id(db, str(user_id))
    return user_data
@limiter.limit("5/minute")
@router.get("/refresh")
async def refresh(response: Response, request: Request, token=Depends(refresh_cookie_sheme)):    
    decoded_token = await decode_refresh_token(token)
    access_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    id = decoded_token["id"]
    is_admin = decoded_token["is_admin"]
    payload_access = Token(id=id, is_admin=is_admin, exp=access_exp).model_dump()
    access_token = await create_access_token(payload_access)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    return {"status": "successful"}
@limiter.limit("5/minute")
@router.post("/login")
async def login_user(data: LogInUser, request: Request, response: Response):
    from main import get_db
    db = get_db(request)
    user_data = await get_user_by_name(db, data.user_name)
    is_valid = await asyncio.to_thread(check_pw, data.password, user_data["password"])
    if not is_valid:
        raise HTTPException(status_code=403)
    id = user_data["id"]
    access_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, is_admin="False", exp=access_exp).model_dump()
    payload_refresh = Token(id=id, is_admin="False", exp=refresh_exp).model_dump()
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    return {"status": "successful"}
@limiter.limit("5/minute")
@router.post("/signup/admin")
async def admin_signup(data: TeacherLoginData, request: Request, response: Response):
    from main import get_db
    if data.admin_code != admin_code:
        raise HTTPException(status_code=401)
    id = str(uuid.uuid4())
    access_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, is_admin="True", exp=access_exp).model_dump()
    payload_refresh = Token(id=id, is_admin="True", exp=refresh_exp).model_dump()
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    db = get_db(request)
    password = await asyncio.to_thread(hash_pw, data.password)
    await create_user(db, id, data.user_name, data.name, password.decode(), "True")
    return {"status":"successful"}
@limiter.limit("5/minute")
@router.post("/login/admin")
async def login(data: TeacherLoginData, request: Request, response: Response):
    from main import get_db
    from services import admin_code
    db = get_db(request)
    if data.admin_code != admin_code:
        raise HTTPException(status_code=403)
    user_data = await get_user_by_name(db, data.user_name)
    is_valid = await asyncio.to_thread(check_pw, data.password, user_data["password"])
    if not is_valid:
        raise HTTPException(status_code=403)
    id = user_data["id"]
    access_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
    refresh_exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
    payload_access = Token(id=id, is_admin="True", exp=access_exp).model_dump()
    payload_refresh = Token(id=id, is_admin="True", exp=refresh_exp).model_dump()
    access_token = await create_access_token(payload_access)
    refresh_token = await create_refresh_token(payload_refresh)
    response.set_cookie(httponly=True, key="access_token", value=access_token, samesite="lax", expires=60*15)
    response.set_cookie(httponly=True, key="refresh_token", value=refresh_token, samesite="lax", expires=24*60*30*60)
    return {"status": "successful"}
@limiter.limit("5/minute")
@router.post("/admin/add_task")
async def add_task(data: Task, files: list[UploadFile] | None, request: Request, user_id=Depends(get_admin)):
    if files:
        for file in files:
            filename = file.filename()
            filename = os.path.basename()
            path = os.path.join("static", filename)
            if os.path.isfile(path):
                raise HTTPException(status_code=502, detail=f"Файл с названием {filename} уже есть на сервере")
            async with aiofiles.open(path, "wb") as f:
                while content := await file.read(1024 * 1024):  
                    await f.write(content) 
    from main import get_db
    db = get_db(request)
    id = str(uuid.uuid4())
    await create_task(db, id, data.name,data.number, data.diff, data.text, data.answer, data.description)
    return {"status": "successful"}
@limiter.limit("5/minute")
@router.get("/tasks/{id}")
async def get_task_id(id, request: Request):
    from main import get_db
    db = get_db(request)
    task = await get_task_by_id(db, id)
    del task["answer"]
    return task 
@limiter.limit("5/minute")
@router.get("/tasks/{id}/check")
async def get_task_check(id, answer, request: Request):
    from main import get_db
    db = get_db(request)
    task = await get_answer_by_id(db, id)
    if answer != task["answer"]:
        return {"status": "False"}
    return {"status": "True"}
@limiter.limit("5/minute")
@router.get("/tasks")
async def get_task(number, request: Request):
    from main import get_db
    db = get_db(request)
    data = await get_tasks_by_number(db, number)
    del data["answer"]
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
            data = await ws.receive_json()
            if len(data["code"]) > 1000:
                await ws.send_text("Извини, но твой код ОООООЧЕНЬ длинный, я не могу его обработать")
            elif len(data["comment"]) > 400:
                await ws.send_text("Можешь пж покороче обьяснить чем тебе помочь, твой запрос оч длинный")
            else:
                input = {
                "system_prompt": "Тебе на вход подаются: условие задачи, код ученика (может быть пустым) и комментарий/вопрос ученика. Тебе нужно ответить на вопросы ученика и помочь ему с задачей. Если запрос ученика не связан с информатикой, то отвечай, что ты можешь помочь только с информатикой. Также твой ответ не должен быть длиннее 600 символов. В ответе можешь использовать html теги для переноса строки/выделения текста и проч, чтобы ответ отображался красиво. Если задачу можно решать кодом, то обьясняй как решать ее кодом",
                "prompt": f"Условие задачи: {data["task"]} Код ученика: {data["code"]} Комментарий/вопрос ученика: {data["comment"]}",
                "max_tokens": 600
                }
                if proxy_url:
                    transport = httpx.AsyncHTTPTransport(proxy=httpx.Proxy(url=proxy_url))
                    client = Client(transport=transport)
                
                    output = await client.async_run("qwen/qwen3-7-plus", input=input)
                    await ws.send_text("".join(output))
    except WebSocketDisconnect:
        logging.debug("websocket connection closed")



