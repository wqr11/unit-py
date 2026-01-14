from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
import os
from sqlalchemy import exc
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request
from jose import jwt, JWTError, ExpiredSignatureError
from dotenv import load_dotenv
import uvicorn
import redis.asyncio as aioredis
from sqlalchemy.orm import Session
from models.subject import Subject
from models.User import Users
from models.labs import Labs
from BaseModel.UserRegBase import UserRegBase
from BaseModel.BaseJoin import BaseJoin
from BaseModel.LabsBase import LabsBase
from BaseModel.Lab_test import LabTestBase
from BaseModel.UpdateBase import UpdateBase
from BaseModel.UserLoginBase import UserLoginBase
from BaseModel.BaseSubject import BaseSubject
from unit import *
from models.db_session import global_init, create_session
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from argon2 import PasswordHasher
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks
from email_utils import send_report_email
from chat.openai import client
import json

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
ACCESS_TOKEN_COOKIE = str(os.getenv("ACCESS_TOKEN_COOKIE"))
REFRESH_TOKEN_COOKIE = str(os.getenv("REFRESH_TOKEN_COOKIE"))
ALLOW_ORIGINS_HEADER = str(os.getenv("ALLOW_ORIGINS_HEADER"))

redis_host = os.getenv("REDIS_HOST")
redis_port = int(os.getenv("REDIS_PORT", 6379))


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

global_init()
app = FastAPI()
redis_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)


def get_db():
    db = create_session()
    try:
        yield db
    finally:
        db.close()


def json_to_email_text(
    result_json, first_name="", last_name="", student_code="", ai_feedback=None
):
    lines = []

    # Информация об авторе
    if first_name or last_name:
        lines.append(f"Тест прошёл: {first_name} {last_name}".strip())
        lines.append("")

    # Код студента
    if student_code:
        lines.append("Код студента:")
        lines.append(student_code)
        lines.append("")

    # Основная информация
    lines.append(f"✅ Correct: {result_json['correct']}")
    lines.append(
        f"Пройдено тестов: {result_json['passed_tests']} из {result_json['total_tests']}"
    )
    lines.append(f"Процент успешных тестов: {result_json['success_rate'] * 100:.1f}%\n")

    # Ошибки общего уровня
    if result_json.get("errors"):
        lines.append("Ошибки:")
        for err in result_json["errors"]:
            lines.append(f"  - {err}")
        lines.append("")

    # Логи
    if result_json.get("logs"):
        lines.append("Логи:")
        for log in result_json["logs"]:
            lines.append(f"  {log}")
        lines.append("")

    # Подробные результаты
    if result_json.get("detailed_results"):
        lines.append("Подробные результаты тестов:")
        for dr in result_json["detailed_results"]:
            lines.append(
                f"Тест #{dr['test_number']}: {'✅' if dr['correct'] else '❌'}"
            )
            lines.append(f"  Входные данные: {dr['input']}")
            lines.append(f"  Ожидаемый вывод: {dr['expected_output']}")
            lines.append(f"  Фактический вывод: {dr['actual_output']}")
            if dr.get("error"):
                lines.append(f"  Ошибка: {dr['error']}")
            if dr.get("diff"):
                lines.append(f"  Diff:\n{dr['diff']}")
            if dr.get("log"):
                lines.append(f"  Лог:\n{dr['log']}")
            lines.append("")

    # Комментарии от ИИ с указанием места ошибки
    if ai_feedback and ai_feedback.get("errors"):
        lines.append("💡 Комментарии от ИИ:")
        student_lines = student_code.split("\n")
        for e in ai_feedback["errors"]:
            row = e["row"]
            code_line = student_lines[row - 1] if 0 < row <= len(student_lines) else ""

            # стрелочки под всю строку (пока нет точного столбца)
            pointer_line = " " * 0 + "∧" * len(code_line) if code_line else ""

            lines.append(f"{row} | {code_line}")
            if pointer_line:
                lines.append(pointer_line)
            lines.append(f"{e['error_message']}")
            lines.append("")

    return "\n".join(lines)


def verify_token(request: Request):
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Access token missing")

    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_user_id_from_cookie(request: Request) -> str:
    """
    Извлекает user_id (str) из JWT токена, хранящегося в cookies.
    Подходит для UUID в строковом формате (например, uuid64).
    """
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token in cookies",
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: user_id missing",
            )
        return str(user_id)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    token_id = str(uuid4())
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh", "jti": token_id})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def save_cookies(response, access, refresh):
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access,
        httponly=False,  # защищает от JS-доступа
        secure=False,  # True в проде (HTTPS)
        samesite="lax",  # можно strict/lax/none
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh,
        httponly=False,  # защищает от JS-доступа
        secure=False,  # True в проде (HTTPS)
        samesite="lax",  # можно strict/lax/none
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 3600 * 24,
    )


async def save_in_redis(user_id: str, token: str):
    await redis_client.setex(
        f"refresh:{user_id}", REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, token
    )


def hashed_password(password):
    ph = PasswordHasher()
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


@app.get("/")
def test():
    return example()


@app.get("/me")
def handleGetMe(res: Response, req: Request, db_sess: Session = Depends(get_db)):
    try:
        user_id = get_user_id_from_cookie(req)
        user = db_sess.query(Users).filter(Users.id == user_id).first()
        return user
    except:
        raise HTTPException(status_code=500, detail="Error on /me request")


@app.post("/register")
def register(user: UserRegBase, db_sess: Session = Depends(get_db)):
    try:
        if db_sess.query(Users).filter(Users.email == user.email).first():
            raise HTTPException(status_code=401, detail="Email already register")
        new_user = Users(
            id=str(uuid4()), email=user.email, password=hashed_password(user.password), is_teacher=user.is_teacher
        )
        db_sess.add(new_user)
        db_sess.commit()
        db_sess.refresh(new_user)
    except exc.StatementError as f:
        print(f)
        raise HTTPException(status_code=400, detail="Bad request")
    else:
        return {"id": new_user.id}


@app.post("/refresh")
async def refresh_token(
    response: Response, request: Request, db_sess: Session = Depends(get_db)
):
    try:
        refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        stored_token = await redis_client.get(f"refresh:{user_id}")
        if not stored_token:
            raise HTTPException(
                status_code=401, detail="Refresh token revoked or expired"
            )
        new_redresh_token = create_refresh_token({"sub": user_id})
        new_access_token = create_access_token({"sub": user_id})
        await save_in_redis(user_id, new_redresh_token)
        save_cookies(response, new_access_token, new_redresh_token)
        return {"messege": "ok"}
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.post("/login")
async def login(
    response: Response, user: UserLoginBase, db_sess: Session = Depends(get_db)
):
    try:
        db_user = db_sess.query(Users).filter(Users.email == user.email).first()
        print(type(db_user))
        print(db_user is None)
        if db_user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not verify_password(user.password, str(db_user.password)):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        access_token = create_access_token(data={"sub": str(db_user.id)})
        refresh_token = create_refresh_token(data={"sub": str(db_user.id)})
        save_cookies(response, access_token, refresh_token)
        await save_in_redis(str(db_user.id), refresh_token)

        if not (access_token and refresh_token):
            raise HTTPException(
                status_code=500, detail="No access or refresh tokens were acquired"
            )

        return {"access_token": access_token, "refresh_token": refresh_token}
    except exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad requests")
    except:
        raise HTTPException(status_code=401, detail="Not found")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOW_ORIGINS_HEADER],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Accept", "Content-Type", "Cookie"],
)


@app.post("/labs", dependencies=[Depends(verify_token)])
def load_data(requests: Request, data: LabsBase, db_sess: Session = Depends(get_db)):
    try:
        user_id = get_user_id_from_cookie(requests)
        new_labs = Labs(
            id=str(uuid4()),
            data_input=data.data_input,
            data_output=data.data_output,
            comment_for_ai=data.comment_for_ai,
            subject_id=data.subject_id,
            user_id=user_id,
            name=data.name,
            task=data.task
        )
        db_sess.add(new_labs)
        db_sess.commit()
        db_sess.refresh(new_labs)
    except exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad request")
    else:
        return new_labs


@app.post("/labs/{id}/test")
async def handle_lab_test(
    student_code: LabTestBase, id: str, db_sess: Session = Depends(get_db)
):
    # получаем лабораторную
    lab = db_sess.query(Labs).filter(Labs.id == id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found")

    # извлекаем входные и ожидаемые данные
    inputs = [lab.data_input]
    expected_outputs = [lab.data_output]

    # тестируем студенческий код
    tester = UnitTester()
    result = tester.run_tests(student_code.student_code, inputs, expected_outputs)

    # возвращаем результат тестирования
    return result


@app.post("/labs/{id}/test-send")
async def handle_lab_test(
    student_code: LabTestBase,
    background_tasks: BackgroundTasks,
    id: str,
    db_sess: Session = Depends(get_db),
):
    try:
        # получаем лабораторную
        lab = db_sess.query(Labs).filter(Labs.id == id).first()
        if not lab:
            raise HTTPException(status_code=404, detail="Lab not found")

        # извлекаем входные и ожидаемые данные
        inputs = [lab.data_input]
        expected_outputs = [lab.data_output]

        # тестируем студенческий код
        tester = UnitTester()
        result = tester.run_tests(student_code.student_code, inputs, expected_outputs)

        # получаем email владельца лабораторной
        user_email = (
            db_sess.query(Users.email).join(Labs).filter(Labs.id == id).scalar()
        )
        if not user_email:
            raise HTTPException(status_code=404, detail="User email not found")
        comm_ai = None
        try:
            comm_ai = client.validate_task(
                f"Код студента:\n{student_code.student_code}\n\nКомментарии преподавателя:\n{lab.comment_for_ai}"
            )
        except:
            print("[ОШИБКА] Не удалось подключиться к ИИ модели!")

        ai_result = json.loads(comm_ai["output_text"]) if comm_ai != None else ""
        
        text = json_to_email_text(
            result,
            student_code.name,
            student_code.surname,
            student_code.student_code,
            ai_result,
        )
        try:
            await send_report_email(user_email, text)
            result["email_delivered"] = True
        except:
            result["email_delivered"] = False
        # @TODO: Fix -- this is temporary
        # background_tasks.add_task(send_report_email, user_email, text)

        return result

    except Exception as e:
        print(f"❌ Ошибка при обработке лабораторной: {e}")
        raise HTTPException(status_code=400, detail="Bad request")


@app.patch("/labs/{id}", dependencies=[Depends(verify_token)])
def update_labs(
    request: Request,
    update_labs: UpdateBase,
    id: str,
    db_sess: Session = Depends(get_db),
):
    try:
        labs = db_sess.query(Labs).get(id)
        user_id = get_user_id_from_cookie(request)
        if labs:
            if labs.user_id != user_id:
                raise HTTPException(status_code=400, detail="Not found")
            labs.name = update_labs.name
            labs.data_input = update_labs.data_input
            labs.data_output = update_labs.data_output
            labs.comment_for_ai = update_labs.comment_for_ai
            db_sess.commit()
            db_sess.refresh(labs)
        else:
            raise HTTPException(status_code=400, detail="Not found")
    except exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad request")
    else:
        return labs


@app.get("/subjects/labs/{subject_id}")
def handle_list_labs_by_subject_id(subject_id: str, db_sess: Session = Depends(get_db)):
    return db_sess.query(Labs).where(Labs.subject_id == subject_id).all()


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


@app.delete("/labs/{id}", dependencies=[Depends(verify_token)])
def delete_post(request: Request, id: str, db_sess: Session = Depends(get_db)):
    try:
        del_labs = db_sess.query(Labs).get(id)
        user_id = get_user_id_from_cookie(request)
        if del_labs:
            if del_labs.user_id != user_id:
                raise HTTPException(status_code=400, detail="Not found")
        if del_labs:
            db_sess.delete(del_labs)
            db_sess.commit()
        else:
            raise HTTPException(status_code=400, detail="Not found")
    except exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad request")
    else:
        return {"detail": "deleted successfully"}


@app.post("/join", dependencies=[Depends(verify_token)])
def join(request: Request, data: BaseJoin, db_sess: Session = Depends(get_db)):
    try:
        cur_user = db_sess.query(Users).get(get_user_id_from_cookie(request))
        subject = db_sess.query(Subject).filter(Subject.id == data.subject_id).first()
        if not subject:
            raise HTTPException(status_code=401, detail="Not found")
        if subject.pass_key != data.pass_key:
            raise HTTPException(status_code=403, detail="Invalid pass key")
        # 3. Проверяем, не записан ли пользователь уже
        if subject in cur_user.enrolled_subjects:
            raise HTTPException(status_code=400, detail="Already joined")

        # 4. Добавляем студента в предмет
        cur_user.enrolled_subjects.append(subject)

        # 5. Сохраняем изменения
        db_sess.commit()

        return {"message": f"You successfully joined '{subject.name}'"}
    except exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad request")
    else:
        return {"message": f"You successfully joined '{subject.name}'"}


@app.get("/subjects")
def handle_subjects_list(request: Request, db_sess: Session = Depends(get_db)):
    try:
        subjects = db_sess.query(Subject).all()
        return subjects
    except:
        raise HTTPException(status_code=500, detail="Couldn't list /subjects")


@app.post("/subjects", dependencies=[Depends(verify_token)])
def create_subject(
    request: Request, data: BaseSubject, db_sess: Session = Depends(get_db)
):
    try:
        user_id = get_user_id_from_cookie(request)
        new_subject = Subject(
            id=str(uuid4()), name=data.name, pass_key=data.pass_key, author_id=user_id
        )
        db_sess.add(new_subject)
        db_sess.commit()
        db_sess.refresh(new_subject)
    except exc.StatementError:
        raise HTTPException(status_code=400, detail="Bad request")
    else:
        return new_subject

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
