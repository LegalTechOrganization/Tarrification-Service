from fastapi import HTTPException, Header
from typing import Optional
from app.models.schemas import GatewayAuthContext, AuthUser, UserOrganization
import json
import logging
import jwt
from app.config import settings

logger = logging.getLogger(__name__)

async def verify_gateway_auth(x_user_data: Optional[str] = Header(None, alias="X-User-Data")):
    """
    Проверка аутентификации через Gateway.
    Gateway передает JWT токен в заголовке X-User-Data.
    Мы сами декодируем токен и извлекаем sub.
    
    Ожидаемый формат:
    {
        "jwt_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
        "user_data": {
            "email": "string", 
            "full_name": "string",
            "orgs": [{"org_id": "string", "name": "string", "role": "string"}],
            "active_org_id": "string"
        }
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
        
        # Получаем JWT токен
        jwt_token = auth_data.get("jwt_token")
        if not jwt_token:
            raise HTTPException(
                status_code=401,
                detail="Missing JWT token in X-User-Data header"
            )
        
        # Декодируем JWT токен (без проверки подписи для демо)
        # В продакшене нужно добавить проверку подписи
        try:
            jwt_payload = jwt.decode(jwt_token, options={"verify_signature": False})
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid JWT token: {str(e)}"
            )
        
        # Извлекаем sub из JWT токена
        sub = jwt_payload.get("sub")
        if not sub:
            raise HTTPException(
                status_code=401,
                detail="Missing sub claim in JWT token"
            )
        
        # Получаем дополнительные данные пользователя
        user_data = auth_data.get("user_data", {})
        
        # Создаем объекты организаций
        orgs = []
        for org_data in user_data.get("orgs", []):
            if isinstance(org_data, dict) and all(k in org_data for k in ["org_id", "name", "role"]):
                orgs.append(UserOrganization(**org_data))
        
        # Создаем объект пользователя
        user = AuthUser(
            sub=sub,  # sub из JWT токена
            email=user_data.get("email", ""),
            full_name=user_data.get("full_name"),
            orgs=orgs,
            active_org_id=user_data.get("active_org_id")
        )
        
        # Создаем контекст аутентификации
        auth_context = GatewayAuthContext(
            user=user,
            jwt_payload=jwt_payload,
            token_valid=True
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
