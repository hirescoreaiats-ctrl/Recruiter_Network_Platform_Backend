import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.config import settings


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    def override():
        db=TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db]=override
    old=settings.upload_dir; old_pictures=settings.profile_picture_dir
    settings.upload_dir=tmp_path/'uploads'; settings.profile_picture_dir=tmp_path/'profile-pictures'
    with TestClient(app) as c: yield c
    settings.upload_dir=old; settings.profile_picture_dir=old_pictures
    app.dependency_overrides.clear(); Base.metadata.drop_all(engine)


def register(client, role, email, profile):
    r=client.post('/api/auth/register',json={"name":role.replace('_',' ').title(),"email":email,"password":"Password123!","role":role,"phone":"1234567890","profile":profile})
    assert r.status_code==201, r.text
    return r.json()


def auth(token): return {"Authorization":f"Bearer {token}"}
