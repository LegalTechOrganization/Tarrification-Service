from sqlalchemy import Column, String, Integer, Boolean, DateTime, func, UniqueConstraint, Float, Text
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class UserBalance(Base):
    """Баланс пользователя"""
    __tablename__ = "user_balances"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sub = Column(String, nullable=False, unique=True, index=True)
    balance_units = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class BalanceTransaction(Base):
    """Журнал транзакций баланса"""
    __tablename__ = "balance_transactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sub = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False)  # 'debit' или 'credit'
    units = Column(Float, nullable=False)
    ref = Column(String, nullable=False)  # Внешний ID операции
    reason = Column(String, nullable=False)  # Причина транзакции
    source_service = Column(String, nullable=True)  # Сервис-источник
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('sub', 'ref', 'direction', name='uq_transaction_idempotency'),
    )

class TariffPlan(Base):
    """Тарифные планы"""
    __tablename__ = "tariff_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    plan_code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    monthly_units = Column(Float, nullable=False, default=0.0)
    price_rub = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserPlan(Base):
    """Активные планы пользователей"""
    __tablename__ = "user_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    sub = Column(String, nullable=False, index=True)
    plan_code = Column(String, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    auto_renew = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('sub', 'plan_code', name='uq_user_plan'),
    ) 