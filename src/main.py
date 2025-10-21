from datetime import timedelta
from typing import Optional
from uuid import uuid4
from argon2 import verify_password
from fastapi import *
from jose import jwt
from models.db_session import global_init
from src.models.User import Users
from unit import *
from models import db_session
import uvicorn
from models.labs import Labs
from BaseModel.LabsBase import LabsBase
from BaseModel.Lab_test import LabTestBase
from sqlalchemy.orm import Session
import sqlalchemy
from BaseModel.UpdateBase import UpdateBase
from dotenv import load_dotenv
from datetime import datetime
import os
from BaseModel.UserRegBase import UserRegBase
import redis.asyncio as aioredis

# Загружаем переменные из .env
load_dotenv()

# Получаем значения
postgres_user = os.getenv("POSTGRES_USER")
postgres_password = os.getenv("POSTGRES_PASSWORD")
postgres_db = os.getenv("POSTGRES_DB")
postgres_url = os.getenv("POSTGRES_URL")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

redis_host = os.getenv("REDIS_HOST")
redis_port = int(os.getenv("REDIS_PORT", 6379))

app = FastAPI()
global_init()
redis_client = aioredis.Redis(host="localhost", port=6379, decode_responses=True)


def get_db():
    db = db_session.create_session()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, db_sess: Session, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    token_id = str(uuid4())
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh", "jti": token_id})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def save_cookies(response, access, refresh):
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,  # защищает от JS-доступа
        secure=False,  # True в проде (HTTPS)
        samesite="lax",  # можно strict/lax/none
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=access,
        httponly=True,  # защищает от JS-доступа
        secure=False,  # True в проде (HTTPS)
        samesite="lax",  # можно strict/lax/none
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 3600 * 24
    )

async def save_in_redis(user_id: str, token: str):
    await redis_client.setex(
        f"refresh:{user_id}", REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, token
    )

@app.get("/")
def test():
    return example()


@app.post("/register")
def register(user: UserRegBase, db_sess: Session = Depends(get_db)):
    try:
        if db_sess.query(Users).filter(Users.email == user.email).first():
            raise HTTPException(status_code=400, detail="Email already register")
        new_user = Users(
            id=str(uuid4()),
            email=user.email,
            password=user.password,
            is_student=user.is_student
        )
        db_sess.add(new_user)
        db_sess.commit()
        db_sess.refresh()
    except sqlalchemy.exc.StatementError:
        raise HTTPException(status_code=400, detail='Bad request')
    else:
        return {"id": new_user.id}


@app.post("/login")
def login(response: Response, email: str, password: str, db_sess: Session = Depends(get_db)):
    try:
        db_user = db_sess.query(Users).filter(Users.email == email).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not verify_password(password, db_user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        access_token = create_access_token(data={"sub": str(db_user.id)})
        refresh_token = create_refresh_token(data={"sub": str(db_user.id)}, db_sess=db_sess)
        save_cookies(response, access_token, refresh_token)
        save_in_redis(db_user.id, refresh_token)
    except sqlalchemy.exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad requests")
    else:
        return {"message": "Logged in successfully"}

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


@app.patch("/labs/{id}")
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


@app.get("/labs")
def get_all_labs(db_sess: Session = Depends(get_db)):
    return db_sess.query(Labs).all()


@app.get("/labs/{id}")
def read_db(id: str, db_sess: Session = Depends(get_db)):
    lab = db_sess.query(Labs).get(id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    else:
        return lab


@app.post("/labs/{id}")
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
