from fastapi import *
from models.db_session import global_init
from unit import *
from models import db_session
import uvicorn
from models.labs import Labs
from BaseModel.LabsBase import LabsBase
from BaseModel.Lab_test import LabTestBase
from sqlalchemy.orm import Session
import sqlalchemy

app = FastAPI()
global_init("static/db/db.sqlite")


def get_db():
    db = db_session.create_session()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def test():
    return example()


@app.post("/labs")
def load_data(data: LabsBase, db_sess: Session = Depends(get_db)):
    if db_sess.query(Labs).filter(Labs.id == data.id).first():
        raise HTTPException(status_code=400, detail="Id already registered")
    try:
        new_labs = Labs(
            id=data.id,
            data_input=data.data_input,
            data_output=data.data_output
        )
        db_sess.add(new_labs)
        db_sess.commit()
        db_sess.refresh(new_labs)
    except sqlalchemy.exc.StatementError:
        raise HTTPException(status_code=400, detail='Bad request')
    else:
        return new_labs


@app.post("/labs/{id}/test")
def handle_lab_test(student_code: LabTestBase, id: str, db_sess: Session = Depends(get_db)):
    try:
        labs = db_sess.query(Labs).get(id)
        inputs = [labs.data_input]
        expected_outputs = [labs.data_output]
        tester = UnitTester()
        result = tester.run_tests(student_code.student_code, inputs, expected_outputs)
    except Exception:
        raise HTTPException(status_code=400, detail='Bad request')
    else:
        return result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
