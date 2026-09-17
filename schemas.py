from pydantic import BaseModel
import datetime
class Token(BaseModel):
    id: str 
    exp: datetime.datetime
class StudentLoginData(BaseModel):
    name: str
    surname: str
    password: str
    grade: str
class TeacherLoginData(BaseModel):
    name: str 
    surname: str 
    password: str