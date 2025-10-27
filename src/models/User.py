# models/users.py
from sqlalchemy import String, Column
from sqlalchemy.orm import relationship
from models.db_session import SqlAlchemyBase

class Users(SqlAlchemyBase):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    # связь с Labs (один ко многим)
    labs = relationship("Labs", back_populates="user", cascade="all, delete-orphan")
