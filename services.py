import jwt 
import dotenv 
import os
dotenv.load_dotenv()
secret = os.getenv("jwt_secret")
async def create_access_token(payload):
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token 
async def decode_access_token(token):
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return payload 
async def create_refresh_token(payload):
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token 
async def decode_refresh_token(token):
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return payload 



