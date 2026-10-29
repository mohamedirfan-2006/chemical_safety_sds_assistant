from fastapi import APIRouter
from backend.app.api.endpoints import router as sds_router

api_router = APIRouter()
api_router.include_router(sds_router, prefix="/sds", tags=["sds"])
