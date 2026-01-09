from pydantic import BaseModel


class LabsBase(BaseModel):
    data_input: str
    data_output: str
    comment_for_ai: str
    name: str
    task: str
    subject_id: str