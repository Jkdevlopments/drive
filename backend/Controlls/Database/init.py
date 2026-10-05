from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base,sessionmaker
import os

load_dotenv()

db_url=os.getenv("DB_URL")
engine=create_engine(db_url)

session_loacl=sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    
)

Base=declarative_base()


def get_db():
    db=session_loacl()
    try:
        yield db
    finally:
        db.close()
        
