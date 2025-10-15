from pydantic import BaseModel


class LabsBase(BaseModel):
    data_input: str
    data_output: str