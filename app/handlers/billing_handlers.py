"""
Обработчики Kafka событий для billing операций
"""
import logging
from typing import Dict, Any
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.kafka_session import get_db_session
from app.services.balance_service import BalanceService
from app.services.plan_service import PlanService
from app.services.kafka_service import kafka_service
from app.models.kafka_models import (
    KafkaEvent, EventType, EventStatus, 
    BalanceCheckPayload, DebitPayload, CreditPayload, PlanApplyPayload,
    BalanceCheckResponsePayload, DebitResponsePayload, CreditResponsePayload, PlanApplyResponsePayload,
    TransactionDetails, PlanDetails, CreditAdjustment,
    AuditEventType, AuditEventData
)
from app.models.schemas import (
    CheckBalanceRequest, DebitRequest, CreditRequest, ApplyPlanRequest
)

logger = logging.getLogger(__name__)

class BillingEventHandler:
    """Обработчик событий биллинга"""
    
    def __init__(self):
        self.balance_service = BalanceService()
        self.plan_service = PlanService()
        
    async def handle_balance_check(self, event_data: Dict[str, Any]):
        """Обработка проверки баланса"""
        session = None
        try:
            # Парсим событие
            event = KafkaEvent(**event_data)
            payload = BalanceCheckPayload(**event.payload)
            
            logger.info(f"Processing balance check for user {payload.user_id}, request {event.request_id}")
            
            # Получаем сессию БД
            session = await get_db_session()
            
            # Создаем внутренний запрос
            internal_request = CheckBalanceRequest(
                user_id=payload.user_id,
                units=payload.units
            )
            
            # Выполняем проверку баланса
            allowed, balance = await self.balance_service.check_balance(session, internal_request)
            
            # Создаем ответ
            response_payload = BalanceCheckResponsePayload(
                allowed=allowed,
                balance=balance,
                quota_info={
                    "action": payload.action,
                    "units_requested": payload.units,
                    "check_result": "allowed" if allowed else "denied"
                }
            )
            
            # Отправляем ответ
            await kafka_service.send_response(
                request_id=event.request_id,
                operation=EventType.BALANCE_CHECK_RESPONSE,
                status=EventStatus.SUCCESS,
                payload=response_payload.dict()
            )
            
            # Отправляем аудит событие
            await kafka_service.send_audit_event(
                event_type=AuditEventType.BALANCE_CHECK_REQUESTED,
                data=AuditEventData(
                    user_id=payload.user_id,
                    org_id=payload.user_context.active_org_id,
                    action=payload.action,
                    amount=payload.units,
                    balance_before=balance,
                    balance_after=balance
                )
            )
            
            logger.info(f"Balance check completed for user {payload.user_id}: allowed={allowed}, balance={balance}")
            
        except Exception as e:
            logger.error(f"Error processing balance check: {e}")
            
            # Отправляем ответ об ошибке
            if 'event' in locals():
                await kafka_service.send_response(
                    request_id=event.request_id,
                    operation=EventType.BALANCE_CHECK_RESPONSE,
                    status=EventStatus.ERROR,
                    error=f"Internal error: {str(e)}"
                )
        finally:
            if session:
                await session.close()

    async def handle_debit(self, event_data: Dict[str, Any]):
        """Обработка списания средств"""
        session = None
        try:
            # Парсим событие
            event = KafkaEvent(**event_data)
            payload = DebitPayload(**event.payload)
            
            logger.info(f"Processing debit for user {payload.user_id}, amount {payload.units}, request {event.request_id}")
            
            # Получаем сессию БД
            session = await get_db_session()
            
            # Создаем внутренний запрос
            internal_request = DebitRequest(
                user_id=payload.user_id,
                units=payload.units,
                ref=payload.ref,
                reason=payload.reason
            )
            
            # Получаем баланс до операции
            balance_before = await self.balance_service.get_balance(session, payload.user_id)
            
            # Выполняем списание
            new_balance, tx_id = await self.balance_service.debit_balance(session, internal_request)
            
            # Создаем детали транзакции
            transaction_details = TransactionDetails(
                amount_debited=payload.units,
                currency="credits",
                timestamp=datetime.utcnow().isoformat() + "Z",
                ref=payload.ref
            )
            
            # Создаем ответ
            response_payload = DebitResponsePayload(
                balance=new_balance,
                tx_id=tx_id,
                transaction_details=transaction_details
            )
            
            # Отправляем ответ
            await kafka_service.send_response(
                request_id=event.request_id,
                operation=EventType.DEBIT_RESPONSE,
                status=EventStatus.SUCCESS,
                payload=response_payload.dict()
            )
            
            # Отправляем аудит событие
            await kafka_service.send_audit_event(
                event_type=AuditEventType.DEBIT_PROCESSED,
                data=AuditEventData(
                    user_id=payload.user_id,
                    org_id=payload.user_context.active_org_id,
                    action=payload.action,
                    amount=payload.units,
                    balance_before=balance_before,
                    balance_after=new_balance,
                    tx_id=tx_id,
                    ref=payload.ref,
                    reason=payload.reason
                )
            )
            
            logger.info(f"Debit completed for user {payload.user_id}: amount={payload.units}, new_balance={new_balance}")
            
        except ValueError as e:
            # Ошибки валидации (недостаточно средств, дублирование и т.д.)
            logger.warning(f"Debit validation error: {e}")
            
            if 'event' in locals():
                await kafka_service.send_response(
                    request_id=event.request_id,
                    operation=EventType.DEBIT_RESPONSE,
                    status=EventStatus.ERROR,
                    error=str(e)
                )
                
                # Отправляем аудит событие об ошибке
                if 'payload' in locals():
                    await kafka_service.send_audit_event(
                        event_type=AuditEventType.INSUFFICIENT_FUNDS,
                        data=AuditEventData(
                            user_id=payload.user_id,
                            org_id=payload.user_context.active_org_id,
                            action=payload.action,
                            amount=payload.units,
                            error_details=str(e)
                        )
                    )
        except Exception as e:
            logger.error(f"Error processing debit: {e}")
            
            if 'event' in locals():
                await kafka_service.send_response(
                    request_id=event.request_id,
                    operation=EventType.DEBIT_RESPONSE,
                    status=EventStatus.ERROR,
                    error=f"Internal error: {str(e)}"
                )
        finally:
            if session:
                await session.close()

    async def handle_credit(self, event_data: Dict[str, Any]):
        """Обработка пополнения баланса"""
        session = None
        try:
            # Парсим событие
            event = KafkaEvent(**event_data)
            payload = CreditPayload(**event.payload)
            
            logger.info(f"Processing credit for user {payload.user_id}, amount {payload.units}, request {event.request_id}")
            
            # Получаем сессию БД
            session = await get_db_session()
            
            # Создаем внутренний запрос
            internal_request = CreditRequest(
                user_id=payload.user_id,
                units=payload.units,
                ref=payload.ref,
                reason=payload.reason,
                source_service="gateway"
            )
            
            # Получаем баланс до операции
            balance_before = await self.balance_service.get_balance(session, payload.user_id)
            
            # Выполняем пополнение
            new_balance, tx_id = await self.balance_service.credit_balance(session, internal_request)
            
            # Создаем детали транзакции
            transaction_details = TransactionDetails(
                amount_credited=payload.units,
                currency="credits",
                timestamp=datetime.utcnow().isoformat() + "Z",
                ref=payload.ref
            )
            
            # Создаем ответ
            response_payload = CreditResponsePayload(
                balance=new_balance,
                tx_id=tx_id,
                transaction_details=transaction_details
            )
            
            # Отправляем ответ
            await kafka_service.send_response(
                request_id=event.request_id,
                operation=EventType.CREDIT_RESPONSE,
                status=EventStatus.SUCCESS,
                payload=response_payload.dict()
            )
            
            # Отправляем аудит событие
            await kafka_service.send_audit_event(
                event_type=AuditEventType.CREDIT_PROCESSED,
                data=AuditEventData(
                    user_id=payload.user_id,
                    org_id=payload.user_context.active_org_id,
                    action=payload.action,
                    amount=payload.units,
                    balance_before=balance_before,
                    balance_after=new_balance,
                    tx_id=tx_id,
                    ref=payload.ref,
                    reason=payload.reason
                )
            )
            
            logger.info(f"Credit completed for user {payload.user_id}: amount={payload.units}, new_balance={new_balance}")
            
        except Exception as e:
            logger.error(f"Error processing credit: {e}")
            
            if 'event' in locals():
                await kafka_service.send_response(
                    request_id=event.request_id,
                    operation=EventType.CREDIT_RESPONSE,
                    status=EventStatus.ERROR,
                    error=f"Internal error: {str(e)}"
                )
        finally:
            if session:
                await session.close()

    async def handle_plan_apply(self, event_data: Dict[str, Any]):
        """Обработка применения плана"""
        session = None
        try:
            # Парсим событие
            event = KafkaEvent(**event_data)
            payload = PlanApplyPayload(**event.payload)
            
            logger.info(f"Processing plan apply for user {payload.user_id}, plan {payload.plan_id}, request {event.request_id}")
            
            # Получаем сессию БД
            session = await get_db_session()
            
            # Создаем внутренний запрос
            internal_request = ApplyPlanRequest(
                user_id=payload.user_id,
                plan_code=payload.plan_id,
                ref=f"kafka-{event.request_id}",
                auto_renew=False
            )
            
            # Выполняем применение плана
            plan_id, new_balance = await self.plan_service.apply_plan(session, internal_request)
            
            # Создаем детали плана
            plan_details = PlanDetails(
                name=f"Plan {payload.plan_id}",
                billing_cycle="monthly",
                effective_date=datetime.utcnow().isoformat() + "Z",
                expires_at=(datetime.utcnow().replace(month=datetime.utcnow().month + 1)).isoformat() + "Z"
            )
            
            # Создаем ответ
            response_payload = PlanApplyResponsePayload(
                plan_id=plan_id,
                new_balance=new_balance,
                plan_details=plan_details
            )
            
            # Отправляем ответ
            await kafka_service.send_response(
                request_id=event.request_id,
                operation=EventType.PLAN_APPLY_RESPONSE,
                status=EventStatus.SUCCESS,
                payload=response_payload.dict()
            )
            
            # Отправляем аудит событие
            await kafka_service.send_audit_event(
                event_type=AuditEventType.PLAN_APPLIED,
                data=AuditEventData(
                    user_id=payload.user_id,
                    org_id=payload.user_context.active_org_id,
                    plan_id=payload.plan_id,
                    balance_after=new_balance
                )
            )
            
            logger.info(f"Plan apply completed for user {payload.user_id}: plan={payload.plan_id}, new_balance={new_balance}")
            
        except Exception as e:
            logger.error(f"Error processing plan apply: {e}")
            
            if 'event' in locals():
                await kafka_service.send_response(
                    request_id=event.request_id,
                    operation=EventType.PLAN_APPLY_RESPONSE,
                    status=EventStatus.ERROR,
                    error=f"Internal error: {str(e)}"
                )
        finally:
            if session:
                await session.close()

# Глобальный экземпляр обработчика
billing_handler = BillingEventHandler()
