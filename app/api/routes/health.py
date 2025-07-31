from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.config import settings

router = APIRouter(tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    return HealthResponse(
        status="ok",
        version=settings.service_version
    )

@router.get("/ready")
async def readiness_check():
    """Проверка готовности сервиса"""
    return {"status": "ready"} 