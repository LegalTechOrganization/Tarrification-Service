"""
Пример клиента для Gateway, демонстрирующий интеграцию с BillingTariffication-Service
"""
import httpx
import asyncio
from typing import Optional, Dict, Any
from uuid import uuid4
import os

class BillingServiceError(Exception):
    """Базовый класс для ошибок сервиса биллинга"""
    pass

class InsufficientFundsError(BillingServiceError):
    """Недостаточно средств"""
    pass

class DuplicateTransactionError(BillingServiceError):
    """Дублирование транзакции"""
    pass

class BillingServiceClient:
    """Клиент для работы с BillingTariffication-Service"""
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or os.getenv("BILLING_SERVICE_URL", "http://localhost:8001")
        self.token = token or os.getenv("BILLING_SERVICE_TOKEN", "super-secret-dev")
        self.headers = {"X-Internal-Key": self.token}
    
    async def check_balance(self, user_id: str, units: float) -> Dict[str, Any]:
        """
        Проверить достаточно ли средств у пользователя
        
        Args:
            user_id: ID пользователя
            units: Количество единиц для проверки
            
        Returns:
            Dict с полями allowed (bool) и balance (float)
            
        Raises:
            BillingServiceError: При ошибке сервиса
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/internal/billing/check",
                    json={"user_id": user_id, "units": units},
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise BillingServiceError(f"Check balance failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")
    
    async def debit_balance(self, user_id: str, units: float, ref: str, reason: str) -> Dict[str, Any]:
        """
        Списать средства с баланса пользователя
        
        Args:
            user_id: ID пользователя
            units: Количество единиц для списания
            ref: Внешний ID операции (для идемпотентности)
            reason: Причина списания
            
        Returns:
            Dict с полями balance (float) и tx_id (str)
            
        Raises:
            InsufficientFundsError: При недостатке средств
            DuplicateTransactionError: При дублировании транзакции
            BillingServiceError: При других ошибках
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/internal/billing/debit",
                    json={
                        "user_id": user_id,
                        "units": units,
                        "ref": ref,
                        "reason": reason
                    },
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    raise InsufficientFundsError("Недостаточно средств")
                elif response.status_code == 409:
                    raise DuplicateTransactionError("Транзакция уже существует")
                else:
                    raise BillingServiceError(f"Debit failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")
    
    async def get_balance(self, user_id: str) -> Dict[str, Any]:
        """
        Получить текущий баланс и информацию о плане пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Dict с полями balance (float) и plan (dict)
            
        Raises:
            BillingServiceError: При ошибке сервиса
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/internal/billing/balance",
                    params={"user_id": user_id},
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise BillingServiceError(f"Get balance failed: {response.text}")
                    
            except httpx.RequestError as e:
                raise BillingServiceError(f"Connection error: {e}")

# Примеры использования в Gateway

class ChatService:
    """Пример сервиса чата, использующего биллинг"""
    
    def __init__(self):
        self.billing_client = BillingServiceClient()
    
    def calculate_message_cost(self, message: str) -> float:
        """Рассчитать стоимость сообщения"""
        # Простая логика: 1 единица за каждые 100 символов
        return max(1.0, len(message) / 100.0)
    
    async def send_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Отправить сообщение в чате с проверкой баланса
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            
        Returns:
            Результат отправки сообщения
            
        Raises:
            InsufficientFundsError: При недостатке средств
        """
        # 1. Рассчитываем стоимость
        units_needed = self.calculate_message_cost(message)
        
        # 2. Проверяем баланс
        try:
            check_result = await self.billing_client.check_balance(user_id, units_needed)
            if not check_result["allowed"]:
                raise InsufficientFundsError(
                    f"Недостаточно средств. Нужно: {units_needed}, доступно: {check_result['balance']}"
                )
        except BillingServiceError as e:
            # Логируем ошибку и пробрасываем дальше
            print(f"Billing check failed: {e}")
            raise
        
        # 3. Выполняем операцию (отправка сообщения)
        try:
            # Здесь должна быть реальная логика отправки сообщения
            message_result = await self._process_message(user_id, message)
            
            # 4. Списываем средства
            ref = f"chat-{uuid4()}"
            debit_result = await self.billing_client.debit_balance(
                user_id, units_needed, ref, "chat_message"
            )
            
            return {
                "message_id": message_result["id"],
                "sent_at": message_result["timestamp"],
                "cost": units_needed,
                "new_balance": debit_result["balance"],
                "tx_id": debit_result["tx_id"]
            }
            
        except Exception as e:
            # Если операция не удалась, средства не списываются
            print(f"Message processing failed: {e}")
            raise
    
    async def _process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Внутренний метод для обработки сообщения"""
        # Здесь должна быть реальная логика
        return {
            "id": str(uuid4()),
            "timestamp": "2025-01-27T10:00:00Z"
        }

class TemplateService:
    """Пример сервиса шаблонов, использующего биллинг"""
    
    def __init__(self):
        self.billing_client = BillingServiceClient()
    
    def get_template_cost(self, template_type: str) -> float:
        """Получить стоимость генерации шаблона"""
        costs = {
            "contract": 10.0,
            "agreement": 5.0,
            "letter": 3.0,
            "default": 2.0
        }
        return costs.get(template_type, costs["default"])
    
    async def generate_template(self, user_id: str, template_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сгенерировать шаблон с проверкой баланса
        
        Args:
            user_id: ID пользователя
            template_type: Тип шаблона
            params: Параметры для генерации
            
        Returns:
            Результат генерации шаблона
            
        Raises:
            InsufficientFundsError: При недостатке средств
        """
        # 1. Получаем стоимость
        units_needed = self.get_template_cost(template_type)
        
        # 2. Проверяем баланс
        try:
            check_result = await self.billing_client.check_balance(user_id, units_needed)
            if not check_result["allowed"]:
                raise InsufficientFundsError(
                    f"Недостаточно средств для генерации шаблона. Нужно: {units_needed}, доступно: {check_result['balance']}"
                )
        except BillingServiceError as e:
            print(f"Billing check failed: {e}")
            raise
        
        # 3. Выполняем операцию (генерация шаблона)
        try:
            template_result = await self._generate_template_content(template_type, params)
            
            # 4. Списываем средства
            ref = f"template-{uuid4()}"
            debit_result = await self.billing_client.debit_balance(
                user_id, units_needed, ref, f"template_{template_type}"
            )
            
            return {
                "template_id": template_result["id"],
                "content": template_result["content"],
                "cost": units_needed,
                "new_balance": debit_result["balance"],
                "tx_id": debit_result["tx_id"]
            }
            
        except Exception as e:
            # Если операция не удалась, средства не списываются
            print(f"Template generation failed: {e}")
            raise
    
    async def _generate_template_content(self, template_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Внутренний метод для генерации содержимого шаблона"""
        # Здесь должна быть реальная логика генерации
        return {
            "id": str(uuid4()),
            "content": f"Generated {template_type} template with params: {params}"
        }

# Пример использования

async def main():
    """Демонстрация работы клиента"""
    
    # Создаем клиенты
    chat_service = ChatService()
    template_service = TemplateService()
    billing_client = BillingServiceClient()
    
    user_id = "11111111-1111-1111-1111-111111111111"
    
    try:
        # 1. Проверяем баланс
        balance_info = await billing_client.get_balance(user_id)
        print(f"Текущий баланс: {balance_info['balance']}")
        
        # 2. Отправляем сообщение
        try:
            message_result = await chat_service.send_message(user_id, "Привет! Это тестовое сообщение.")
            print(f"Сообщение отправлено: {message_result}")
        except InsufficientFundsError as e:
            print(f"Ошибка отправки сообщения: {e}")
        
        # 3. Генерируем шаблон
        try:
            template_result = await template_service.generate_template(
                user_id, "contract", {"client_name": "ООО Тест", "amount": 100000}
            )
            print(f"Шаблон сгенерирован: {template_result}")
        except InsufficientFundsError as e:
            print(f"Ошибка генерации шаблона: {e}")
        
        # 4. Проверяем финальный баланс
        final_balance = await billing_client.get_balance(user_id)
        print(f"Финальный баланс: {final_balance['balance']}")
        
    except BillingServiceError as e:
        print(f"Ошибка сервиса биллинга: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 