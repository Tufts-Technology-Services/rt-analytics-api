from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from fastapi import HTTPException
from ..models import StorageOwnerStatus, engine
from ..auth import get_user


secure_router = APIRouter()

@secure_router.get("/")
async def get_secure_route(user: dict = Depends(get_user)):
    return user


@secure_router.get("/ncq/eligibility/{username}")
def get_user_eligibility(username: str):
    with Session(engine) as session:
        statement = select(StorageOwnerStatus).where(StorageOwnerStatus.username == username)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
    return {"username": username, "eligibility": result}


@secure_router.get("/ncq/eligibility")
def get_ncq_eligibility(start: int = 0, rows: int = 100):
    with Session(engine) as session:
        statement = select(StorageOwnerStatus).limit(rows).offset(start)
        result = session.exec(statement).all()
        if not result:
            raise HTTPException(status_code=404, detail="No more users found")
    return {"start": start, "rows": rows, "results": result}