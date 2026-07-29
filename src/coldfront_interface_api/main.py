from fastapi import FastAPI, Depends, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select
from typing import List, Optional


DATABASE_URL = "mysql://localhost:3306"
engine = create_engine(DATABASE_URL, connect_args=connect_args)






app = FastAPI()


@app.get("/health")
def read_root():
    return {"status": "OK"}


@app.get("/ncq/eligibility/{username}")
def get_user_eligibility(username: str, q: str | None = None):
    return {"username": username, "q": q}

