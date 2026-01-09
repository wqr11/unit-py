from sqlalchemy import String, Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .db_session import SqlAlchemyBase
from sqlalchemy.sql import func
from .groups import Groups

class Subject(SqlAlchemyBase):
    __tablename__ = "subject"

    id = Column(String, primary_key=True, server_default=func.gen_random_uuid())
    name= Column(String, nullable=False)
    pass_key = Column(String, nullable=False)

    # внешний ключ на Users.id
    author_id = Column(String, ForeignKey("users.id"), nullable=False)

    # обратная связь
    author = relationship("Users", back_populates="subjects")

    labs = relationship("Labs", back_populates="subject", cascade="all, delete")
    
    # студенты, записанные на предмет
    students = relationship(
        "Users",
        secondary=Groups,
        back_populates="enrolled_subjects",
    )