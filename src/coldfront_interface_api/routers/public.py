from fastapi import APIRouter

public_router = APIRouter()

@public_router.get("/health")
async def get_public_route():
    return {"message": "OK"}