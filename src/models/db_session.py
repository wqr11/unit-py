from os import getenv
from dotenv import load_dotenv
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec
from ..logger import log

load_dotenv()

POSTGRES_URL=getenv("POSTGRES_URL")

SqlAlchemyBase = dec.declarative_base()

__factory = None


def global_init():
    global __factory

    if __factory:
        return

    log("info", f"Connecting to database")

    engine = sa.create_engine(POSTGRES_URL, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    import models.__all_models

    log("info", f"Registered tables before create: {SqlAlchemyBase.metadata.tables.keys()}")
    SqlAlchemyBase.metadata.create_all(engine)
    log("info", f"Registered tables after create: {SqlAlchemyBase.metadata.tables.keys()}")



def create_session() -> Session:
    global __factory
    return __factory()
