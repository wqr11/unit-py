from pydantic import BaseModel


class LabsBase(BaseModel):
    id: str
    data_input: str
    data_output: str