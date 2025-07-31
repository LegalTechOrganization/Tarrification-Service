import pytest
from datetime import datetime
from app.models.database import UserBalance, BalanceTransaction, TariffPlan, UserPlan
from app.models.schemas import (
    CheckBalanceRequest, DebitRequest, CreditRequest, ApplyPlanRequest,
    CheckBalanceResponse, DebitResponse, CreditResponse, BalanceResponse, ApplyPlanResponse
)

class TestDatabaseModels:
    """Тесты для моделей базы данных"""
    
    def test_user_balance_creation(self):
        """Тест создания баланса пользователя"""
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=100.0
        )
        
        assert balance.user_id == "test-user-123"
        assert balance.balance_units == 100.0
        assert balance.id is not None
    
    def test_balance_transaction_creation(self):
        """Тест создания транзакции"""
        transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="debit",
            units=10.0,
            ref="test-ref-123",
            reason="test_debit",
            source_service="test_service"
        )
        
        assert transaction.user_id == "test-user-123"
        assert transaction.direction == "debit"
        assert transaction.units == 10.0
        assert transaction.ref == "test-ref-123"
        assert transaction.reason == "test_debit"
        assert transaction.source_service == "test_service"
        assert transaction.id is not None
    
    def test_tariff_plan_creation(self):
        """Тест создания тарифного плана"""
        plan = TariffPlan(
            plan_code="test_plan",
            name="Test Plan",
            monthly_units=500.0,
            price_rub=29900
        )
        
        assert plan.plan_code == "test_plan"
        assert plan.name == "Test Plan"
        assert plan.monthly_units == 500.0
        assert plan.price_rub == 29900
        assert plan.is_active == True
        assert plan.id is not None
    
    def test_user_plan_creation(self):
        """Тест создания плана пользователя"""
        now = datetime.utcnow()
        expires_at = datetime(2025, 12, 31)
        
        user_plan = UserPlan(
            user_id="test-user-123",
            plan_code="test_plan",
            started_at=now,
            expires_at=expires_at,
            auto_renew=True
        )
        
        assert user_plan.user_id == "test-user-123"
        assert user_plan.plan_code == "test_plan"
        assert user_plan.started_at == now
        assert user_plan.expires_at == expires_at
        assert user_plan.auto_renew == True
        assert user_plan.is_active == True
        assert user_plan.id is not None

class TestAPISchemas:
    """Тесты для API схем"""
    
    def test_check_balance_request(self):
        """Тест схемы запроса проверки баланса"""
        request = CheckBalanceRequest(
            user_id="test-user-123",
            units=5.0
        )
        
        assert request.user_id == "test-user-123"
        assert request.units == 5.0
    
    def test_debit_request(self):
        """Тест схемы запроса списания"""
        request = DebitRequest(
            user_id="test-user-123",
            units=10.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        assert request.user_id == "test-user-123"
        assert request.units == 10.0
        assert request.ref == "test-ref-123"
        assert request.reason == "test_debit"
    
    def test_credit_request(self):
        """Тест схемы запроса пополнения"""
        request = CreditRequest(
            user_id="test-user-123",
            units=100.0,
            ref="test-ref-123",
            source_service="test_service",
            reason="test_credit"
        )
        
        assert request.user_id == "test-user-123"
        assert request.units == 100.0
        assert request.ref == "test-ref-123"
        assert request.source_service == "test_service"
        assert request.reason == "test_credit"
    
    def test_apply_plan_request(self):
        """Тест схемы запроса применения плана"""
        request = ApplyPlanRequest(
            user_id="test-user-123",
            plan_code="test_plan",
            ref="test-ref-123",
            auto_renew=True
        )
        
        assert request.user_id == "test-user-123"
        assert request.plan_code == "test_plan"
        assert request.ref == "test-ref-123"
        assert request.auto_renew == True
    
    def test_check_balance_response(self):
        """Тест схемы ответа проверки баланса"""
        response = CheckBalanceResponse(
            allowed=True,
            balance=95.0
        )
        
        assert response.allowed == True
        assert response.balance == 95.0
    
    def test_debit_response(self):
        """Тест схемы ответа списания"""
        response = DebitResponse(
            balance=90.0,
            tx_id="tx-123"
        )
        
        assert response.balance == 90.0
        assert response.tx_id == "tx-123"
    
    def test_credit_response(self):
        """Тест схемы ответа пополнения"""
        response = CreditResponse(
            balance=190.0,
            tx_id="tx-456"
        )
        
        assert response.balance == 190.0
        assert response.tx_id == "tx-456"
    
    def test_balance_response(self):
        """Тест схемы ответа баланса"""
        plan_info = {
            "plan_code": "test_plan",
            "expires_at": "2025-12-31T00:00:00",
            "status": "active"
        }
        
        response = BalanceResponse(
            balance=190.0,
            plan=plan_info
        )
        
        assert response.balance == 190.0
        assert response.plan == plan_info
    
    def test_apply_plan_response(self):
        """Тест схемы ответа применения плана"""
        response = ApplyPlanResponse(
            plan_id="plan-123",
            new_balance=500.0
        )
        
        assert response.plan_id == "plan-123"
        assert response.new_balance == 500.0

class TestValidation:
    """Тесты валидации"""
    
    def test_units_must_be_positive(self):
        """Тест что units должны быть положительными"""
        with pytest.raises(ValueError):
            CheckBalanceRequest(
                user_id="test-user-123",
                units=0.0
            )
        
        with pytest.raises(ValueError):
            CheckBalanceRequest(
                user_id="test-user-123",
                units=-5.0
            )
    
    def test_user_id_required(self):
        """Тест что user_id обязателен"""
        with pytest.raises(ValueError):
            CheckBalanceRequest(
                user_id="",
                units=5.0
            ) 