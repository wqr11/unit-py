from uuid import uuid4
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
from BaseModel.UpdateBase import UpdateBase

app = FastAPI()
global_init()


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
    try:
        new_labs = Labs(
            id=str(uuid4()),
            data_input=data.data_input,
            data_output=data.data_output,
            comment_for_ai=data.comment_for_ai
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


@app.post("/update/{id}")
def update_labs(update_labs: UpdateBase, id: str, db_sess: Session = Depends(get_db)):
    try:
        labs = db_sess.query(Labs).get(id)
        if labs:
            labs.data_input = update_labs.data_input
            labs.data_output = update_labs.data_output
            labs.comment_for_ai = update_labs.comment_for_ai
            db_sess.commit()
            db_sess.refresh(labs)
        else:
            raise HTTPException(status_code=400, detail='Not found')
    except sqlalchemy.exc.StatementError:
        raise HTTPException(status_code=400, detail='Bad request')
    else:
        return labs


@app.get("/read")
def get_all_labs(db_sess: Session = Depends(get_db)):
    return db_sess.query(Labs).all()


@app.get("/read/{id}")
def read_db(id: str, db_sess: Session = Depends(get_db)):
    lab = db_sess.query(Labs).get(id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    else:
        return lab


@app.post("/delete/{id}")
def delete_post(id: str, db_sess: Session = Depends(get_db)):
    try:
        del_labs = db_sess.query(Labs).get(id)
        if del_labs:
            db_sess.delete(del_labs)
            db_sess.commit()
        else:
            raise HTTPException(status_code=400, detail='Not found')
    except sqlalchemy.exc.StatementError:
        raise HTTPException(status_code=400, detail='Bad request')
    else:
        return {"detail": "deleted successfully"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
