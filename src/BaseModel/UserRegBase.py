from pydantic import BaseModel, EmailStr


class UserRegBase(BaseModel):
    email: EmailStr
    password: str