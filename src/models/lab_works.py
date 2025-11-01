from sqlalchemy import Table, Column, String, ForeignKey, PrimaryKeyConstraint
from models.db_session import SqlAlchemyBase

Groups = Table(
    "lab_works",
    SqlAlchemyBase.metadata,
    Column("lab_id", String, ForeignKey("labs.id"), nullable=False),
    Column("subject_id", String, ForeignKey("subject.id"), nullable=False),
    PrimaryKeyConstraint("lab_id", "subject_id"),
)