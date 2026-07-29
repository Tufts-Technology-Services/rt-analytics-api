from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlmodel import Session, select
from pwdlib import PasswordHash
from .models import APIUser, engine

api_key_header = APIKeyHeader(name="X-API-Key")
password_hash = PasswordHash.recommended()

def get_user(api_key_header: str = Security(api_key_header)):
    try:
        user = get_user_from_api_key(api_key_header)
        return user
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key"
        )


def get_user_from_api_key(api_key: str):
    with Session(engine) as session:
        statement = select(APIUser)
        result = session.exec(statement).all()
        # there are never going to be more than a handful of users, so this is fine for now. 
        # If we ever have more than a handful of users, 
        # we should change this to a query that checks for the api_key directly.
        for user in result:
            if password_hash.verify(api_key, user.api_key):
                return {"username": user.username}
        raise HTTPException(status_code=404, detail="User not found")