from os import getenv
from dotenv import load_dotenv
from passlib.context import CryptContext

class Environment:
    postgres_user = str(getenv("POSTGRES_USER"))
    postgres_password = str(getenv("POSTGRES_PASSWORD"))
    postgres_db = str(getenv("POSTGRES_DB"))
    postgres_url = str(getenv("POSTGRES_URL"))

    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

    SECRET_KEY = str(getenv("SECRET_KEY"))
    ALGORITHM = str(getenv("ALGORITHM"))
    ACCESS_TOKEN_COOKIE = str(getenv("ACCESS_TOKEN_COOKIE"))
    REFRESH_TOKEN_COOKIE = str(getenv("REFRESH_TOKEN_COOKIE"))
    ALLOW_ORIGINS_HEADER = str(getenv("ALLOW_ORIGINS_HEADER"))
    ACCESS_TOKEN_EXPIRE_MINUTES = int(getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS = int(getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    redis_host = str(getenv("REDIS_HOST"))
    redis_port = int(getenv("REDIS_PORT", 6379))

    def __init__(self):
        _ = load_dotenv()

ENV = Environment()