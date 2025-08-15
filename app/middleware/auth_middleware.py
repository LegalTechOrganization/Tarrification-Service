from fastapi import HTTPException, Header
from typing import Optional
from app.models.schemas import GatewayAuthContext, AuthUser, UserOrganization
import json
import logging

logger = logging.getLogger(__name__)

async def verify_gateway_auth(x_user_data: Optional[str] = Header(None, alias="X-User-Data")):
    """
    Проверка аутентификации через Gateway.
    Gateway передает данные пользователя в заголовке X-User-Data в JSON формате.
    
    Ожидаемый формат:
    {
        "user": {
            "user_id": "string",
            "email": "string", 
            "full_name": "string",
            "orgs": [{"org_id": "string", "name": "string", "role": "string"}],
            "active_org_id": "string"
        },
        "jwt_payload": {...},
        "token_valid": true
    }
    """
    if not x_user_data:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication data. X-User-Data header is required."
        )
    
    try:
        # Парсим JSON из заголовка
        auth_data = json.loads(x_user_data)
        
        # Проверяем валидность токена
        if not auth_data.get("token_valid", False):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authentication token"
            )
        
        # Извлекаем данные пользователя
        user_data = auth_data.get("user", {})
        if not user_data.get("user_id"):
            raise HTTPException(
                status_code=401,
                detail="Invalid user data: missing user_id"
            )
        
        # Создаем объекты организаций
        orgs = []
        for org_data in user_data.get("orgs", []):
            if isinstance(org_data, dict) and all(k in org_data for k in ["org_id", "name", "role"]):
                orgs.append(UserOrganization(**org_data))
        
        # Создаем объект пользователя
        user = AuthUser(
            user_id=user_data["user_id"],
            email=user_data.get("email", ""),
            full_name=user_data.get("full_name"),
            orgs=orgs,
            active_org_id=user_data.get("active_org_id")
        )
        
        # Создаем контекст аутентификации
        auth_context = GatewayAuthContext(
            user=user,
            jwt_payload=auth_data.get("jwt_payload"),
            token_valid=auth_data.get("token_valid", True)
        )
        
        return auth_context
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse X-User-Data header: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid X-User-Data format: not valid JSON"
        )
    except Exception as e:
        logger.error(f"Error processing authentication data: {e}")
        raise HTTPException(
            status_code=401,
            detail="Failed to process authentication data"
        )

async def verify_internal_key(x_internal_key: Optional[str] = Header(None)):
    """
    Проверка внутреннего ключа для прямых вызовов (legacy).
    Используется для обратной совместимости.
    """
    # Пока оставляем как есть для совместимости
    return x_internal_key

async def get_user_from_context(auth_context: GatewayAuthContext) -> AuthUser:
    """Извлечь пользователя из контекста аутентификации"""
    if not auth_context.token_valid:
        raise HTTPException(
            status_code=401,
            detail="Authentication token is not valid"
        )
    
    return auth_context.user
