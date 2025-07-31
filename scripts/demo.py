#!/usr/bin/env python3
"""
Демонстрационный скрипт для показа работы BillingTariffication-Service
"""

import asyncio
import httpx
from datetime import datetime

class BillingServiceDemo:
    """Демонстрация работы сервиса биллинга"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.internal_key = "super-secret-dev"
        self.headers = {"X-Internal-Key": self.internal_key}
    
    async def demo_health_check(self):
        """Демонстрация проверки здоровья сервиса"""
        print("🏥 Проверка здоровья сервиса...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Статус: {data['status']}")
                print(f"   Версия: {data['version']}")
            print()
    
    async def demo_check_balance(self, user_id: str = "demo-user-123"):
        """Демонстрация проверки баланса"""
        print(f"💰 Проверка баланса пользователя: {user_id}")
        
        request_data = {
            "user_id": user_id,
            "units": 5.0
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/billing/check",
                json=request_data,
                headers=self.headers
            )
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Достаточно средств: {data['allowed']}")
                print(f"   Текущий баланс: {data['balance']}")
            print()
    
    async def demo_get_balance(self, user_id: str = "demo-user-123"):
        """Демонстрация получения баланса"""
        print(f"💳 Получение баланса пользователя: {user_id}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/internal/billing/balance?user_id={user_id}",
                headers=self.headers
            )
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Баланс: {data['balance']}")
                if data['plan']:
                    print(f"   План: {data['plan']['plan_code']}")
                    print(f"   Статус: {data['plan']['status']}")
            print()
    
    async def demo_credit_balance(self, user_id: str = "demo-user-123"):
        """Демонстрация пополнения баланса"""
        print(f"➕ Пополнение баланса пользователя: {user_id}")
        
        request_data = {
            "user_id": user_id,
            "units": 100.0,
            "ref": f"demo-credit-{datetime.now().strftime('%H%M%S')}",
            "source_service": "demo",
            "reason": "demo_credit"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/billing/credit",
                json=request_data,
                headers=self.headers
            )
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Новый баланс: {data['balance']}")
                print(f"   ID транзакции: {data['tx_id']}")
            print()
    
    async def demo_debit_balance(self, user_id: str = "demo-user-123"):
        """Демонстрация списания баланса"""
        print(f"➖ Списание с баланса пользователя: {user_id}")
        
        request_data = {
            "user_id": user_id,
            "units": 2.0,
            "ref": f"demo-debit-{datetime.now().strftime('%H%M%S')}",
            "reason": "demo_debit"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/billing/debit",
                json=request_data,
                headers=self.headers
            )
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Новый баланс: {data['balance']}")
                print(f"   ID транзакции: {data['tx_id']}")
            elif response.status_code == 403:
                print("   ❌ Недостаточно средств")
            print()
    
    async def demo_apply_plan(self, user_id: str = "demo-user-123"):
        """Демонстрация применения плана"""
        print(f"📋 Применение плана для пользователя: {user_id}")
        
        request_data = {
            "user_id": user_id,
            "plan_code": "base750",
            "ref": f"demo-plan-{datetime.now().strftime('%H%M%S')}",
            "auto_renew": False
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/internal/billing/plan/apply",
                json=request_data,
                headers=self.headers
            )
            print(f"   Статус: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ID плана: {data['plan_id']}")
                print(f"   Новый баланс: {data['new_balance']}")
            elif response.status_code == 404:
                print("   ❌ План не найден")
            print()
    
    async def demo_idempotency(self, user_id: str = "demo-user-123"):
        """Демонстрация идемпотентности"""
        print(f"🔄 Демонстрация идемпотентности для пользователя: {user_id}")
        
        ref = f"idempotency-test-{datetime.now().strftime('%H%M%S')}"
        
        # Первый вызов
        request_data = {
            "user_id": user_id,
            "units": 1.0,
            "ref": ref,
            "reason": "idempotency_test"
        }
        
        async with httpx.AsyncClient() as client:
            # Первый вызов
            response1 = await client.post(
                f"{self.base_url}/internal/billing/debit",
                json=request_data,
                headers=self.headers
            )
            print(f"   Первый вызов - статус: {response1.status_code}")
            
            if response1.status_code == 200:
                data1 = response1.json()
                tx_id1 = data1['tx_id']
                balance1 = data1['balance']
                print(f"   ID транзакции: {tx_id1}")
                print(f"   Баланс: {balance1}")
            
            # Повторный вызов с тем же ref
            response2 = await client.post(
                f"{self.base_url}/internal/billing/debit",
                json=request_data,
                headers=self.headers
            )
            print(f"   Повторный вызов - статус: {response2.status_code}")
            
            if response2.status_code == 200:
                data2 = response2.json()
                tx_id2 = data2['tx_id']
                balance2 = data2['balance']
                print(f"   ID транзакции: {tx_id2}")
                print(f"   Баланс: {balance2}")
                
                if tx_id1 == tx_id2 and balance1 == balance2:
                    print("   ✅ Идемпотентность работает корректно")
                else:
                    print("   ❌ Ошибка идемпотентности")
            print()
    
    async def run_full_demo(self):
        """Запуск полной демонстрации"""
        print("🚀 Демонстрация BillingTariffication-Service")
        print("=" * 50)
        
        try:
            # Проверка здоровья
            await self.demo_health_check()
            
            # Основные операции
            await self.demo_check_balance()
            await self.demo_get_balance()
            await self.demo_credit_balance()
            await self.demo_debit_balance()
            await self.demo_apply_plan()
            await self.demo_idempotency()
            
            # Проверка баланса после операций
            await self.demo_get_balance()
            
            print("✅ Демонстрация завершена успешно!")
            
        except httpx.ConnectError:
            print("❌ Ошибка подключения к сервису")
            print("   Убедитесь, что сервис запущен на http://localhost:8000")
        except Exception as e:
            print(f"❌ Ошибка во время демонстрации: {e}")

if __name__ == "__main__":
    demo = BillingServiceDemo()
    asyncio.run(demo.run_full_demo()) 