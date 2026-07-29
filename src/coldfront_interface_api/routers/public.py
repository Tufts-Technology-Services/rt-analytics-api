from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_public_route():
    return "OK"