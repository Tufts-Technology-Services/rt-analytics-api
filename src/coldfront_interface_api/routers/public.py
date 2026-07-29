from fastapi import APIRouter

public_router = APIRouter()

@public_router.get("/")
async def get_public_route():
    return "OK"