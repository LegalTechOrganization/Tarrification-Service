import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.config import settings
from app.models.kafka_models import (
    KafkaEvent, KafkaResponse, EventStatus, EventType, 
    AuditEvent, AuditEventType, AuditEventData
)

logger = logging.getLogger(__name__)

class KafkaService:
    """Сервис для работы с Kafka"""
    
    def __init__(self):
        self.bootstrap_servers = getattr(settings, 'kafka_bootstrap_servers', 'kafka:29092')
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        
    async def start_producer(self):
        """Запуск Kafka producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                acks='all'  # Ждем подтверждения от всех реплик
            )
            await self.producer.start()
            logger.info("Kafka producer started successfully")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop_producer(self):
        """Остановка Kafka producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def start_consumer(self, topic: str, group_id: str, handler: Callable):
        """Запуск Kafka consumer для топика"""
        try:
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',  # Читаем только новые сообщения
                enable_auto_commit=True,
                consumer_timeout_ms=1000
            )
            
            await consumer.start()
            self.consumers[topic] = consumer
            self.message_handlers[topic] = handler
            
            logger.info(f"Started consumer for topic: {topic} with group: {group_id}")
            
            # Запускаем обработку сообщений в фоне
            asyncio.create_task(self._consume_messages(topic))
            
        except Exception as e:
            logger.error(f"Failed to start consumer for topic {topic}: {e}")
            raise

    async def _consume_messages(self, topic: str):
        """Обработка сообщений из топика"""
        consumer = self.consumers[topic]
        handler = self.message_handlers[topic]
        
        try:
            while self.running:
                try:
                    # Получаем сообщения пакетами
                    msg_pack = await consumer.getmany(timeout_ms=1000)
                    
                    for tp, messages in msg_pack.items():
                        for message in messages:
                            try:
                                # Логируем входящее сообщение
                                logger.info(f"Received message from {topic}: {message.key}")
                                
                                # Обрабатываем сообщение
                                await handler(message.value)
                                
                            except Exception as e:
                                logger.error(f"Error processing message from {topic}: {e}")
                                # Можно добавить отправку в DLQ (Dead Letter Queue)
                                
                except asyncio.TimeoutError:
                    # Нормальный timeout, продолжаем
                    continue
                except Exception as e:
                    logger.error(f"Error in consumer loop for {topic}: {e}")
                    await asyncio.sleep(5)  # Пауза перед повторной попыткой
                    
        except Exception as e:
            logger.error(f"Fatal error in consumer for {topic}: {e}")

    async def stop_consumers(self):
        """Остановка всех consumers"""
        self.running = False
        
        for topic, consumer in self.consumers.items():
            try:
                await consumer.stop()
                logger.info(f"Stopped consumer for topic: {topic}")
            except Exception as e:
                logger.error(f"Error stopping consumer for {topic}: {e}")
                
        self.consumers.clear()
        self.message_handlers.clear()

    async def send_message(self, topic: str, message: Dict[str, Any], key: Optional[str] = None):
        """Отправка сообщения в Kafka топик"""
        if not self.producer:
            raise RuntimeError("Kafka producer not started")
            
        try:
            await self.producer.send(
                topic=topic,
                value=message,
                key=key.encode('utf-8') if key else None
            )
            logger.info(f"Sent message to {topic} with key: {key}")
            
        except KafkaError as e:
            logger.error(f"Failed to send message to {topic}: {e}")
            raise

    async def send_response(self, request_id: str, operation: EventType, 
                          status: EventStatus, payload: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None):
        """Отправка ответа в billing-responses топик"""
        response = KafkaResponse(
            message_id=str(uuid.uuid4()),
            request_id=request_id,
            operation=operation,
            timestamp=datetime.utcnow().isoformat() + "Z",
            status=status,
            payload=payload,
            error=error
        )
        
        await self.send_message(
            topic="billing-responses",
            message=response.dict(),
            key=request_id
        )

    async def send_audit_event(self, event_type: AuditEventType, data: AuditEventData):
        """Отправка события для аудита"""
        event = AuditEvent(
            event_type=event_type,
            timestamp=datetime.utcnow().timestamp(),
            data=data
        )
        
        await self.send_message(
            topic="billing-events",
            message=event.dict(),
            key=data.user_id
        )

    async def start(self):
        """Запуск Kafka сервиса"""
        self.running = True
        await self.start_producer()
        logger.info("Kafka service started")

    async def stop(self):
        """Остановка Kafka сервиса"""
        self.running = False
        await self.stop_consumers()
        await self.stop_producer()
        logger.info("Kafka service stopped")

# Глобальный экземпляр сервиса
kafka_service = KafkaService()
