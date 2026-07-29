import os
from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, create_engine
from .routers import public_router, secure_router
from .auth import get_user

DATABASE_URL = os.getenv("DATABASE_URL", "mysql://localhost:3306")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

create_db_and_tables()
app = FastAPI()

app.include_router(
    public_router,
    prefix="/api/v1/public"
)
app.include_router(
    secure_router,
    prefix="/api/v1/secure",
    dependencies=[Depends(get_user)]
)
