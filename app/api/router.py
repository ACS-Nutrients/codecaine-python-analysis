from fastapi import APIRouter
from app.api.endpoints.analysis import router, router_recommendations

api_router = APIRouter()
api_router.include_router(router)
api_router.include_router(router_recommendations)
