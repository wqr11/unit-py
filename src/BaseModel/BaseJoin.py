from pydantic import BaseModel

class BaseJoin(BaseModel):
    pass_key: str
    subject_id: str