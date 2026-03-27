# server/src/server/api/router.py
from fastapi import APIRouter
from server.api.upload import router as upload_router

api_router = APIRouter(prefix="/api")
api_router.include_router(upload_router)
