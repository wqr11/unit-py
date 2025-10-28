from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS") == "True",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS") == "True",
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


async def send_report_email(to: EmailStr, report_text: str):
    message = MessageSchema(
        subject="Ваш отчёт готов ✅",
        recipients=[to],  # можно список
        body=f"Здравствуйте!\n\nВаш отчёт:\n{report_text}\n\nС уважением,\nСистема отчётов",
        subtype="plain"  # можно "html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
