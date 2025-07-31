import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.balance_service import BalanceService
from app.services.plan_service import PlanService
from app.models.schemas import CheckBalanceRequest, DebitRequest, CreditRequest, ApplyPlanRequest
from app.models.database import UserBalance, BalanceTransaction, TariffPlan, UserPlan
from fastapi import HTTPException

class TestBalanceService:
    """Тесты для BalanceService"""
    
    @pytest.fixture
    def balance_service(self):
        return BalanceService()
    
    @pytest.mark.asyncio
    async def test_check_balance_sufficient_funds(self, balance_service):
        """Тест проверки баланса с достаточными средствами"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=100.0
        )
        
        request = CheckBalanceRequest(
            user_id="test-user-123",
            units=50.0
        )
        
        with patch.object(balance_service.balance_dao, 'get_or_create_balance', return_value=balance):
            allowed, current_balance = await balance_service.check_balance(mock_session, request)
            
            assert allowed == True
            assert current_balance == 100.0
    
    @pytest.mark.asyncio
    async def test_check_balance_insufficient_funds(self, balance_service):
        """Тест проверки баланса с недостаточными средствами"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=30.0
        )
        
        request = CheckBalanceRequest(
            user_id="test-user-123",
            units=50.0
        )
        
        with patch.object(balance_service.balance_dao, 'get_or_create_balance', return_value=balance):
            allowed, current_balance = await balance_service.check_balance(mock_session, request)
            
            assert allowed == False
            assert current_balance == 30.0
    
    @pytest.mark.asyncio
    async def test_debit_balance_success(self, balance_service):
        """Тест успешного списания средств"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=100.0
        )
        
        transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="debit",
            units=20.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        request = DebitRequest(
            user_id="test-user-123",
            units=20.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        with patch.object(balance_service.transaction_dao, 'get_by_ref_and_direction', return_value=None), \
             patch.object(balance_service.balance_dao, 'get_or_create_balance', return_value=balance), \
             patch.object(balance_service.balance_dao, 'update_balance'), \
             patch.object(balance_service.transaction_dao, 'create_transaction', return_value=transaction):
            
            new_balance, tx_id = await balance_service.debit_balance(mock_session, request)
            
            assert new_balance == 80.0  # 100 - 20
            assert tx_id == transaction.id
            balance_service.balance_dao.update_balance.assert_called_once_with(mock_session, "test-user-123", 80.0)
    
    @pytest.mark.asyncio
    async def test_debit_balance_insufficient_funds(self, balance_service):
        """Тест списания при недостаточных средствах"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=10.0
        )
        
        request = DebitRequest(
            user_id="test-user-123",
            units=20.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        with patch.object(balance_service.transaction_dao, 'get_by_ref_and_direction', return_value=None), \
             patch.object(balance_service.balance_dao, 'get_or_create_balance', return_value=balance):
            
            with pytest.raises(HTTPException) as exc_info:
                await balance_service.debit_balance(mock_session, request)
            
            assert exc_info.value.status_code == 403
            assert "quota_exceeded" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_debit_balance_idempotency(self, balance_service):
        """Тест идемпотентности списания"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        existing_transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="debit",
            units=20.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=80.0
        )
        
        request = DebitRequest(
            user_id="test-user-123",
            units=20.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        with patch.object(balance_service.transaction_dao, 'get_by_ref_and_direction', return_value=existing_transaction), \
             patch.object(balance_service.balance_dao, 'get_by_user_id', return_value=balance):
            
            new_balance, tx_id = await balance_service.debit_balance(mock_session, request)
            
            assert new_balance == 80.0
            assert tx_id == existing_transaction.id
    
    @pytest.mark.asyncio
    async def test_credit_balance_success(self, balance_service):
        """Тест успешного пополнения баланса"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=50.0
        )
        
        transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="credit",
            units=100.0,
            ref="test-ref-123",
            reason="test_credit"
        )
        
        request = CreditRequest(
            user_id="test-user-123",
            units=100.0,
            ref="test-ref-123",
            source_service="test_service",
            reason="test_credit"
        )
        
        with patch.object(balance_service.transaction_dao, 'get_by_ref_and_direction', return_value=None), \
             patch.object(balance_service.balance_dao, 'get_or_create_balance', return_value=balance), \
             patch.object(balance_service.balance_dao, 'update_balance'), \
             patch.object(balance_service.transaction_dao, 'create_transaction', return_value=transaction):
            
            new_balance, tx_id = await balance_service.credit_balance(mock_session, request)
            
            assert new_balance == 150.0  # 50 + 100
            assert tx_id == transaction.id
            balance_service.balance_dao.update_balance.assert_called_once_with(mock_session, "test-user-123", 150.0)
    
    @pytest.mark.asyncio
    async def test_credit_balance_idempotency(self, balance_service):
        """Тест идемпотентности пополнения"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        existing_transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="credit",
            units=100.0,
            ref="test-ref-123",
            reason="test_credit"
        )
        
        balance = UserBalance(
            user_id="test-user-123",
            balance_units=150.0
        )
        
        request = CreditRequest(
            user_id="test-user-123",
            units=100.0,
            ref="test-ref-123",
            source_service="test_service",
            reason="test_credit"
        )
        
        with patch.object(balance_service.transaction_dao, 'get_by_ref_and_direction', return_value=existing_transaction), \
             patch.object(balance_service.balance_dao, 'get_by_user_id', return_value=balance):
            
            new_balance, tx_id = await balance_service.credit_balance(mock_session, request)
            
            assert new_balance == 150.0
            assert tx_id == existing_transaction.id

class TestPlanService:
    """Тесты для PlanService"""
    
    @pytest.fixture
    def plan_service(self):
        return PlanService()
    
    @pytest.mark.asyncio
    async def test_apply_plan_success(self, plan_service):
        """Тест успешного применения плана"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        tariff_plan = TariffPlan(
            plan_code="test_plan",
            name="Test Plan",
            monthly_units=500.0,
            price_rub=29900
        )
        
        user_plan = UserPlan(
            user_id="test-user-123",
            plan_code="test_plan",
            started_at="2025-01-01T00:00:00",
            expires_at="2025-12-31T00:00:00",
            is_active=True
        )
        
        request = ApplyPlanRequest(
            user_id="test-user-123",
            plan_code="test_plan",
            ref="test-ref-123",
            auto_renew=False
        )
        
        with patch.object(plan_service.plan_dao, 'get_tariff_plan', return_value=tariff_plan), \
             patch.object(plan_service.plan_dao, 'apply_plan', return_value=user_plan), \
             patch.object(plan_service.balance_service, 'credit_balance', return_value=(500.0, "tx-123")):
            
            plan_id, new_balance = await plan_service.apply_plan(mock_session, request)
            
            assert plan_id == user_plan.id
            assert new_balance == 500.0
    
    @pytest.mark.asyncio
    async def test_apply_plan_not_found(self, plan_service):
        """Тест применения несуществующего плана"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        request = ApplyPlanRequest(
            user_id="test-user-123",
            plan_code="invalid_plan",
            ref="test-ref-123",
            auto_renew=False
        )
        
        with patch.object(plan_service.plan_dao, 'get_tariff_plan', return_value=None):
            with pytest.raises(ValueError, match="Tariff plan not found"):
                await plan_service.apply_plan(mock_session, request)
    
    @pytest.mark.asyncio
    async def test_get_user_plan_info_with_plan(self, plan_service):
        """Тест получения информации о плане пользователя"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        user_plan = UserPlan(
            user_id="test-user-123",
            plan_code="test_plan",
            started_at="2025-01-01T00:00:00",
            expires_at="2025-12-31T00:00:00",
            is_active=True
        )
        
        with patch.object(plan_service.plan_dao, 'get_active_plan_by_user', return_value=user_plan):
            plan_info = await plan_service.get_user_plan_info(mock_session, "test-user-123")
            
            assert plan_info is not None
            assert plan_info["plan_code"] == "test_plan"
            assert plan_info["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_user_plan_info_no_plan(self, plan_service):
        """Тест получения информации о плане когда план отсутствует"""
        mock_session = AsyncMock(spec=AsyncSession)
        
        with patch.object(plan_service.plan_dao, 'get_active_plan_by_user', return_value=None):
            plan_info = await plan_service.get_user_plan_info(mock_session, "test-user-123")
            
            assert plan_info is None 