#!/usr/bin/env python3
"""
Тест интеграции с Auth Service через Gateway
"""
import requests
import json

# Данные пользователя от Auth Service (как их передаст Gateway)
auth_context = {
    "user": {
        "user_id": "99b37077-1509-4dd6-8a34-635b00cfae62",
        "email": "pen1s@example.com",
        "full_name": "Test User",
        "orgs": [
            {
                "org_id": "org-123",
                "name": "Test Organization",
                "role": "admin"
            }
        ],
        "active_org_id": "org-123"
    },
    "jwt_payload": {
        "sub": "99b37077-1509-4dd6-8a34-635b00cfae62",
        "email": "pen1s@example.com",
        "exp": 1723121231
    },
    "token_valid": True
}

# Заголовки запроса
headers = {
    "Content-Type": "application/json",
    "X-User-Data": json.dumps(auth_context)
}

BASE_URL = "http://localhost:8001/internal/billing"

def test_check_balance():
    """Тест проверки баланса"""
    print("=== Тест проверки баланса ===")
    
    payload = {
        "action": "chat",
        "units": 5.0,
        "auth_context": auth_context
    }
    
    response = requests.post(f"{BASE_URL}/check", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def test_get_balance():
    """Тест получения баланса"""
    print("=== Тест получения баланса ===")
    
    payload = {
        "auth_context": auth_context
    }
    
    response = requests.post(f"{BASE_URL}/balance", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def test_debit_balance():
    """Тест списания средств"""
    print("=== Тест списания средств ===")
    
    payload = {
        "action": "chat",
        "units": 2.0,
        "reason": "chat_message",
        "ref": "test-chat-001",
        "auth_context": auth_context
    }
    
    response = requests.post(f"{BASE_URL}/debit", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def test_credit_balance():
    """Тест пополнения баланса"""
    print("=== Тест пополнения баланса ===")
    
    payload = {
        "action": "deposit",
        "units": 10.0,
        "reason": "test_deposit",
        "ref": "test-deposit-001",
        "auth_context": auth_context
    }
    
    response = requests.post(f"{BASE_URL}/credit", json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

def test_legacy_endpoint():
    """Тест legacy эндпоинта"""
    print("=== Тест legacy эндпоинта ===")
    
    response = requests.get(f"{BASE_URL}/balance?user_id=99b37077-1509-4dd6-8a34-635b00cfae62")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()

if __name__ == "__main__":
    print("Тестирование интеграции с Auth Service")
    print("="*50)
    
    try:
        test_check_balance()
        test_get_balance()
        test_credit_balance()  # Сначала пополним
        test_debit_balance()   # Потом спишем
        test_legacy_endpoint() # Проверим legacy
        print("✅ Все тесты завершены")
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
