from fastapi import FastAPI, Depends
from .routers import public_router, secure_router
from .auth import get_user

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
