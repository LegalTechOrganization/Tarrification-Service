import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException
import os

class MicroserviceClient:
    def __init__(self):
        self.base_urls = {
            "billing": "http://localhost:8001",  # URL твоего микросервиса
            # Добавь другие микросервисы по мере необходимости
        }
        
        # Получаем токен из переменных окружения
        self.service_token = os.getenv("BILLING_SERVICE_TOKEN", "super-secret-dev")
        
        # Заголовки для аутентификации
        self.headers = {
            "X-Internal-Key": self.service_token,
            "Content-Type": "application/json"
        }
    
    async def proxy_request(
        self, 
        service_name: str, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Проксирует запрос к микросервису"""
        if service_name not in self.base_urls:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        url = f"{self.base_urls[service_name]}{path}"
        
        async with httpx.AsyncClient() as client:
            try:
                # Добавляем заголовки аутентификации
                headers = self.headers.copy()
                
                if method.upper() == "GET":
                    # Для GET запросов добавляем X-Internal-Key в параметры
                    if params is None:
                        params = {}
                    params["X-Internal-Key"] = self.service_token
                    response = await client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, params=params, headers=headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, params=params, headers=headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, params=params, headers=headers)
                else:
                    raise HTTPException(status_code=400, detail=f"Method {method} not supported")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                # Пробрасываем HTTP ошибки как есть
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
            except httpx.RequestError as e:
                raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable: {str(e)}")

# Создаём экземпляр клиента
microservice_client = MicroserviceClient() 