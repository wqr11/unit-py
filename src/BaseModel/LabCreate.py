from pydantic import BaseModel

class LabCreate(BaseModel):
    title: str
    description: str
    subject_id: int