from pydantic import BaseModel


class UpdateBase(BaseModel):
    data_input: str
    data_output: str
    comment_for_ai: str