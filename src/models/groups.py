from sqlalchemy import Table, Column, String, ForeignKey, PrimaryKeyConstraint
from models.db_session import SqlAlchemyBase

Groups = Table(
    "groups",
    SqlAlchemyBase.metadata,
    Column("student_id", String, ForeignKey("users.id"), nullable=False),
    Column("subject_id", String, ForeignKey("subject.id"), nullable=False),
    PrimaryKeyConstraint("student_id", "subject_id"),
)