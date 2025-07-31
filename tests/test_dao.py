import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.balance_dao import BalanceDAO
from app.repositories.transaction_dao import TransactionDAO
from app.repositories.plan_dao import PlanDAO
from app.models.database import UserBalance, BalanceTransaction, TariffPlan, UserPlan


@pytest.fixture
def mock_session():
    """Мок сессии БД"""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


class TestBalanceDAO:
    """Тесты для BalanceDAO"""
    
    @pytest.mark.asyncio
    async def test_get_by_user_id(self):
        """Тест получения баланса по user_id"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = BalanceDAO()
        
        # Мокаем результат запроса
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = UserBalance(
            user_id="test-user-123",
            balance_units=100.0
        )
        mock_session.execute.return_value = mock_result
        
        result = await dao.get_by_user_id(mock_session, "test-user-123")
        
        assert result.user_id == "test-user-123"
        assert result.balance_units == 100.0
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_or_create_balance_existing(self):
        """Тест получения существующего баланса"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = BalanceDAO()
        
        existing_balance = UserBalance(
            user_id="test-user-123",
            balance_units=50.0
        )
        
        # Мокаем get_by_user_id
        with patch.object(dao, 'get_by_user_id', return_value=existing_balance):
            result = await dao.get_or_create_balance(mock_session, "test-user-123")
            
            assert result == existing_balance
            assert result.balance_units == 50.0
    
    @pytest.mark.asyncio
    async def test_get_or_create_balance_new(self):
        """Тест создания нового баланса"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = BalanceDAO()
        
        new_balance = UserBalance(
            user_id="test-user-123",
            balance_units=0.0
        )
        
        # Мокаем get_by_user_id возвращает None
        with patch.object(dao, 'get_by_user_id', return_value=None), \
             patch.object(dao, 'create', return_value=new_balance):
            result = await dao.get_or_create_balance(mock_session, "test-user-123")
            
            assert result == new_balance
            dao.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_balance(self):
        """Тест обновления баланса"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = BalanceDAO()
        
        updated_balance = UserBalance(
            user_id="test-user-123",
            balance_units=150.0
        )
        
        with patch.object(dao, 'get_by_user_id', return_value=updated_balance):
            result = await dao.update_balance(mock_session, "test-user-123", 150.0)
            
            assert result == updated_balance
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

class TestTransactionDAO:
    """Тесты для TransactionDAO"""
    
    @pytest.mark.asyncio
    async def test_get_by_ref_and_direction(self):
        """Тест получения транзакции по ref и direction"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = TransactionDAO()
        
        transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="debit",
            units=10.0,
            ref="test-ref-123",
            reason="test_debit"
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = transaction
        mock_session.execute.return_value = mock_result
        
        result = await dao.get_by_ref_and_direction(
            mock_session, "test-user-123", "test-ref-123", "debit"
        )
        
        assert result == transaction
        assert result.direction == "debit"
        assert result.ref == "test-ref-123"
    
    @pytest.mark.asyncio
    async def test_create_transaction(self):
        """Тест создания транзакции"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = TransactionDAO()
        
        transaction = BalanceTransaction(
            user_id="test-user-123",
            direction="credit",
            units=100.0,
            ref="test-ref-123",
            reason="test_credit",
            source_service="test_service"
        )
        
        with patch.object(dao, 'create', return_value=transaction):
            result = await dao.create_transaction(
                mock_session, "test-user-123", "credit", 100.0,
                "test-ref-123", "test_credit", "test_service"
            )
            
            assert result == transaction
            dao.create.assert_called_once()

class TestPlanDAO:
    """Тесты для PlanDAO"""
    
    @pytest.mark.asyncio
    async def test_get_active_plan_by_user(self):
        """Тест получения активного плана пользователя"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = PlanDAO()
        
        user_plan = UserPlan(
            user_id="test-user-123",
            plan_code="test_plan",
            started_at="2025-01-01T00:00:00",
            expires_at="2025-12-31T00:00:00",
            is_active=True
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_plan
        mock_session.execute.return_value = mock_result
        
        result = await dao.get_active_plan_by_user(mock_session, "test-user-123")
        
        assert result == user_plan
        assert result.plan_code == "test_plan"
        assert result.is_active == True
    
    @pytest.mark.asyncio
    async def test_get_tariff_plan(self):
        """Тест получения тарифного плана"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = PlanDAO()
        
        tariff_plan = TariffPlan(
            plan_code="test_plan",
            name="Test Plan",
            monthly_units=500.0,
            price_rub=29900
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = tariff_plan
        mock_session.execute.return_value = mock_result
        
        result = await dao.get_tariff_plan(mock_session, "test_plan")
        
        assert result == tariff_plan
        assert result.plan_code == "test_plan"
        assert result.monthly_units == 500.0
    
    @pytest.mark.asyncio
    async def test_apply_plan(self):
        """Тест применения плана"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = PlanDAO()
        
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
        
        with patch.object(dao, 'get_tariff_plan', return_value=tariff_plan), \
             patch.object(dao, 'deactivate_user_plans'), \
             patch.object(dao, 'create', return_value=user_plan):
            result = await dao.apply_plan(
                mock_session, "test-user-123", "test_plan", "test-ref-123", False
            )
            
            assert result == user_plan
            dao.deactivate_user_plans.assert_called_once()
            dao.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_plan_not_found(self):
        """Тест применения несуществующего плана"""
        mock_session = AsyncMock(spec=AsyncSession)
        dao = PlanDAO()
        
        with patch.object(dao, 'get_tariff_plan', return_value=None):
            with pytest.raises(ValueError, match="Tariff plan not found"):
                await dao.apply_plan(
                    mock_session, "test-user-123", "invalid_plan", "test-ref-123", False
                ) 