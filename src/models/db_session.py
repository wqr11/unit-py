from os import getenv
from dotenv import load_dotenv
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec

load_dotenv()

POSTGRES_URL=getenv("POSTGRES_URL")

SqlAlchemyBase = dec.declarative_base()

__factory = None


def global_init():
    global __factory

    if __factory:
        return

    engine = sa.create_engine(POSTGRES_URL, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    import models.__all_models

    SqlAlchemyBase.metadata.create_all(engine)



def create_session() -> Session:
    global __factory
    return __factory()
