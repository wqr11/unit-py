import os
from datetime import datetime, timedelta
from BaseModel.UserLoginBase import UserLoginBase
from sqlalchemy import exc
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, Request, Response, status
from typing import Optional
from jose import jwt, JWTError
from models.User import Users
from uuid import uuid4
from config.env import ENV
from config.redis import redis_client

class AuthService:
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=ENV.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, ENV.SECRET_KEY, algorithm=ENV.ALGORITHM)
        return encoded_jwt


    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        token_id = str(uuid4())
        expire = datetime.utcnow() + (
            expires_delta or timedelta(days=ENV.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        to_encode.update({"exp": expire, "type": "refresh", "jti": token_id})
        encoded_jwt = jwt.encode(to_encode, ENV.SECRET_KEY, algorithm=ENV.ALGORITHM)
        return encoded_jwt

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return ENV.pwd_context.verify(plain_password, hashed_password)

    def verify_token(self, request: Request):
        token = request.cookies.get(ENV.ACCESS_TOKEN_COOKIE)
        if not token:
            raise HTTPException(status_code=401, detail="Access token missing")

        try:
            jwt.decode(token, ENV.SECRET_KEY, algorithms=[ENV.ALGORITHM])
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")


    def get_user_id_from_cookie(self, request: Request) -> str:
        """
        Извлекает user_id (str) из JWT токена, хранящегося в cookies.
        Подходит для UUID в строковом формате (например, uuid64).
        """
        token = request.cookies.get(ENV.ACCESS_TOKEN_COOKIE)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing token in cookies",
            )

        try:
            payload = jwt.decode(token, ENV.SECRET_KEY, algorithms=[ENV.ALGORITHM])
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

    async def save_in_redis(self, user_id: str, token: str):
        await redis_client.setex(
            f"refresh:{user_id}", ENV.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, token
        )

    async def login(
        self, user: UserLoginBase, db_sess: Session
    ):
        try:
            db_user = db_sess.query(Users).filter(Users.email == user.email).first()
            
            if db_user is None:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            if not self.verify_password(user.password, str(db_user.password)):
                raise HTTPException(status_code=401, detail="Invalid email or password")

            access_token = self.create_access_token(data={"sub": str(db_user.id)})
            refresh_token = self.create_refresh_token(data={"sub": str(db_user.id)})
            
            # save_cookies(response, access_token, refresh_token)
            await self.save_in_redis(str(db_user.id), refresh_token)

            if not (access_token and refresh_token):
                raise HTTPException(
                    status_code=500, detail="No access or refresh tokens were acquired"
                )

            return {"access_token": access_token, "refresh_token": refresh_token}
        
        except exc.StatementError:
            raise HTTPException(status_code=400, detail="Bad requests")
        
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="Unhandled Server Error")

auth_service = AuthService()