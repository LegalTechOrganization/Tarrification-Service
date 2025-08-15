#!/usr/bin/env python3
"""
Тест Kafka интеграции для Billing Service
Симулирует отправку событий от Gateway
"""
import asyncio
import json
import uuid
from datetime import datetime
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

# Конфигурация Kafka
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

async def send_test_event(producer, topic, event_data):
    """Отправляет тестовое событие"""
    try:
        await producer.send(
            topic=topic,
            value=json.dumps(event_data, default=str).encode('utf-8'),
            key=event_data['request_id'].encode('utf-8')
        )
        print(f"✅ Sent event to {topic}: {event_data['request_id']}")
    except KafkaError as e:
        print(f"❌ Failed to send to {topic}: {e}")

async def test_balance_check():
    """Тест проверки баланса"""
    event_data = {
        "message_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "operation": "balance_check",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "user_id": "99b37077-1509-4dd6-8a34-635b00cfae62",
            "action": "chat_message",
            "units": 5.0,
            "user_context": {
                "email": "test@example.com",
                "full_name": "Test User",
                "active_org_id": "org-123",
                "org_role": "admin",
                "is_org_owner": True
            },
            "request_metadata": {
                "source_ip": "192.168.1.100",
                "user_agent": "TestAgent/1.0",
                "gateway_request_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    }
    return event_data

async def test_debit():
    """Тест списания средств"""
    event_data = {
        "message_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "operation": "debit",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "user_id": "99b37077-1509-4dd6-8a34-635b00cfae62",
            "action": "chat_message",
            "units": 2.5,
            "ref": f"test-msg-{uuid.uuid4()}",
            "reason": "GPT-4 chat message processing",
            "user_context": {
                "email": "test@example.com",
                "full_name": "Test User",
                "active_org_id": "org-123",
                "org_role": "admin",
                "is_org_owner": True
            },
            "operation_context": {
                "service_name": "chat",
                "feature": "gpt4_chat",
                "session_id": "sess-789"
            },
            "request_metadata": {
                "source_ip": "192.168.1.100",
                "user_agent": "TestAgent/1.0"
            }
        }
    }
    return event_data

async def test_credit():
    """Тест пополнения баланса"""
    event_data = {
        "message_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "operation": "credit",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "user_id": "99b37077-1509-4dd6-8a34-635b00cfae62",
            "action": "manual_credit",
            "units": 100.0,
            "ref": f"payment-{uuid.uuid4()}",
            "reason": "Monthly subscription renewal",
            "user_context": {
                "email": "test@example.com",
                "full_name": "Test User",
                "active_org_id": "org-123",
                "org_role": "admin",
                "is_org_owner": True
            },
            "payment_context": {
                "payment_method": "stripe",
                "payment_intent_id": "pi_1234567890",
                "subscription_id": "sub_abcdef123456"
            },
            "request_metadata": {
                "source_ip": "192.168.1.100",
                "user_agent": "TestAgent/1.0",
                "admin_user_id": "admin-456"
            }
        }
    }
    return event_data

async def test_plan_apply():
    """Тест применения плана"""
    event_data = {
        "message_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "operation": "plan_apply",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": {
            "user_id": "99b37077-1509-4dd6-8a34-635b00cfae62",
            "plan_id": "enterprise_annual",
            "user_context": {
                "email": "test@example.com",
                "full_name": "Test User",
                "active_org_id": "org-123",
                "org_role": "admin",
                "is_org_owner": True
            },
            "plan_context": {
                "upgrade_from": "pro_monthly",
                "prorate": True,
                "effective_date": datetime.utcnow().isoformat() + "Z"
            },
            "request_metadata": {
                "source_ip": "192.168.1.100",
                "user_agent": "TestAgent/1.0",
                "admin_user_id": "admin-456"
            }
        }
    }
    return event_data

async def main():
    """Основная функция тестирования"""
    print("🚀 Starting Kafka integration test...")
    
    # Создаем producer
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: v  # Уже сериализуем вручную
    )
    
    try:
        await producer.start()
        print("✅ Kafka producer started")
        
        # Ждем немного для стабилизации подключения
        await asyncio.sleep(2)
        
        print("\n📤 Sending test events...")
        
        # Тест 1: Пополняем баланс
        print("\n1️⃣ Testing credit (adding funds)...")
        credit_event = await test_credit()
        await send_test_event(producer, "billing-credit", credit_event)
        await asyncio.sleep(1)
        
        # Тест 2: Проверяем баланс
        print("\n2️⃣ Testing balance check...")
        balance_event = await test_balance_check()
        await send_test_event(producer, "billing-balance-check", balance_event)
        await asyncio.sleep(1)
        
        # Тест 3: Списываем средства
        print("\n3️⃣ Testing debit (spending funds)...")
        debit_event = await test_debit()
        await send_test_event(producer, "billing-debit", debit_event)
        await asyncio.sleep(1)
        
        # Тест 4: Применяем план
        print("\n4️⃣ Testing plan apply...")
        plan_event = await test_plan_apply()
        await send_test_event(producer, "billing-plan-apply", plan_event)
        await asyncio.sleep(1)
        
        print("\n✅ All test events sent!")
        print("📋 Summary:")
        print(f"   • Credit request: {credit_event['request_id']}")
        print(f"   • Balance check: {balance_event['request_id']}")
        print(f"   • Debit request: {debit_event['request_id']}")
        print(f"   • Plan apply: {plan_event['request_id']}")
        
        print("\n⏳ Check billing service logs for processing results...")
        print("   docker compose logs billing-service -f")
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
    finally:
        await producer.stop()
        print("\n🛑 Kafka producer stopped")

if __name__ == "__main__":
    asyncio.run(main())
