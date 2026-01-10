# models/labs.py
from sqlalchemy import String, Column, ForeignKey
from sqlalchemy.orm import relationship
from .db_session import SqlAlchemyBase

class Labs(SqlAlchemyBase):
    __tablename__ = "labs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    task = Column(String, nullable=True)
    data_input = Column(String, nullable=True)
    data_output = Column(String, nullable=True)
    comment_for_ai = Column(String, nullable=True)

    # внешний ключ на Users.id
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    subject_id = Column(String, ForeignKey("subject.id", ondelete="CASCADE"), nullable=False)
    subject = relationship("Subject", back_populates="labs")

    # обратная связь
    user = relationship("Users", back_populates="labs")
