from pydantic import BaseModel


class LabTestBase(BaseModel):
    student_code: str
    name: str
    surname: str
    group: str