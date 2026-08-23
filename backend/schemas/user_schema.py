from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    gender: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str