import jwt 
import dotenv 
import os
import bcrypt
import base64
dotenv.load_dotenv()
secret = os.getenv("JWT")
admin_code = os.getenv("ADMIN_CODE")
proxy_url = os.getenv("PROXY")
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



def hash_pw(password):
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(password.encode(), salt)
    return hash
def check_pw(password, hashed_password):
    return bcrypt.checkpw(password, hashed_password=hashed_password)
