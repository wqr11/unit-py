# models/users.py
from sqlalchemy import String, Column, Boolean
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase
from .groups import Groups

class Users(SqlAlchemyBase):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    is_teacher = Column(Boolean, default=False)

    # связь с Labs (один ко многим)
    labs = relationship("Labs", back_populates="user", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="author", cascade="all, delete-orphan")

    # many-to-many: предметы, на которые студент записан
    enrolled_subjects = relationship(
        "Subject",
        secondary=Groups,
        back_populates="students",
    )
