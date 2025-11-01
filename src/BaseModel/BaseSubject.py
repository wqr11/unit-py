from pydantic import BaseModel

class BaseSubject(BaseModel):
    name: str
    pass_key: str