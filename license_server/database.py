# license_server/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from models import Base

def get_database_url(config_path: str) -> str:
    import json
    with open(config_path) as f:
        config = json.load(f)
    return config['license_server']['database_url']

def get_engine(config_path: str):
    database_url = get_database_url(config_path)
    return create_engine(database_url, connect_args={"check_same_thread": False})

def get_session(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def init_db(engine):
    Base.metadata.create_all(bind=engine)
