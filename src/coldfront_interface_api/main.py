import os
from fastapi import FastAPI, HTTPException
from sqlmodel import Session, SQLModel, create_engine, select
from .models import StorageOwnerStatus


DATABASE_URL = os.getenv("DATABASE_URL", "mysql://localhost:3306")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

app = FastAPI()


@app.get("/health")
def read_root():
    return {"status": "OK"}


@app.get("/ncq/eligibility/{username}")
def get_user_eligibility(username: str, q: str | None = None):
    with Session(engine) as session:
        statement = select(StorageOwnerStatus).where(StorageOwnerStatus.username == username)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, "q": q, "eligibility": result}


@app.get("/ncq/eligibility")
def get_ncq_eligibility(start: int = 0, rows: int = 100):
    with Session(engine) as session:
        statement = select(StorageOwnerStatus).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No more users found")
    return {"start": start, "rows": rows, "results": result}
