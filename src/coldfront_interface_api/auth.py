from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select
from .models import APIUser
from .main import engine

api_key_header = APIKeyHeader(name="X-API-Key")

def get_user(api_key_header: str = Security(api_key_header)):
    if check_api_key(api_key_header):
        user = get_user_from_api_key(api_key_header)
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid API key"
    )

def check_api_key(api_key: str) -> bool:
    with Session(engine) as session:
        statement = select(APIUser).where(APIUser.api_key == api_key)
        result = session.exec(statement).first()
        if not result:
            return False
    return True

def get_user_from_api_key(api_key: str):
    with Session(engine) as session:
        statement = select(APIUser).where(APIUser.api_key == api_key)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
    return {"username": result.username}