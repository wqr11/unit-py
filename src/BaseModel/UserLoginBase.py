from pydantic import BaseModel, EmailStr


class UserLoginBase(BaseModel):
    email: EmailStr
    password: str