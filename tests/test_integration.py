import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.main import app
from app.database.connection import get_db
from app.models.database import UserBalance, BalanceTransaction, TariffPlan, UserPlan

@pytest.fixture
async def client():
    """Тестовый клиент с моком БД"""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    
    app.dependency_overrides[get_db] = lambda: mock_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user_balance():
    """Мок баланса пользователя"""
    balance = UserBalance(
        user_id="test-user-123",
        balance_units=100.0
    )
    balance.id = "balance-123"
    return balance

@pytest.fixture
def mock_transaction():
    """Мок транзакции"""
    transaction = BalanceTransaction(
        user_id="test-user-123",
        direction="debit",
        units=10.0,
        ref="test-ref-123",
        reason="test_debit"
    )
    transaction.id = "tx-123"
    return transaction

@pytest.fixture
def mock_tariff_plan():
    """Мок тарифного плана"""
    plan = TariffPlan(
        plan_code="test_plan",
        name="Test Plan",
        monthly_units=500.0,
        price_rub=29900
    )
    plan.id = "tariff-123"
    return plan

@pytest.fixture
def mock_user_plan():
    """Мок плана пользователя"""
    from datetime import datetime
    plan = UserPlan(
        user_id="test-user-123",
        plan_code="test_plan",
        started_at=datetime(2025, 1, 1),
        expires_at=datetime(2025, 12, 31),
        is_active=True
    )
    plan.id = "user-plan-123"
    return plan

class TestBillingServiceIntegration:
    """Интеграционные тесты для полного цикла работы сервиса"""
    
    @pytest.mark.asyncio
    async def test_check_balance_success(self, client, mock_user_balance):
        """Тест успешной проверки баланса"""
        with patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance):
            response = await client.post(
                "/internal/billing/check",
                json={
                    "user_id": "test-user-123",
                    "units": 50.0
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] == True
            assert data["balance"] == 100.0
    
    @pytest.mark.asyncio
    async def test_check_balance_insufficient_funds(self, client, mock_user_balance):
        """Тест проверки баланса с недостаточными средствами"""
        with patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance):
            response = await client.post(
                "/internal/billing/check",
                json={
                    "user_id": "test-user-123",
                    "units": 150.0
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] == False
            assert data["balance"] == 100.0
    
    @pytest.mark.asyncio
    async def test_debit_balance_success(self, client, mock_user_balance, mock_transaction):
        """Тест успешного списания средств"""
        with patch('app.services.balance_service.TransactionDAO.get_by_ref_and_direction', return_value=None), \
             patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance), \
             patch('app.services.balance_service.BalanceDAO.update_balance'), \
             patch('app.services.balance_service.TransactionDAO.create_transaction', return_value=mock_transaction):
            
            response = await client.post(
                "/internal/billing/debit",
                json={
                    "user_id": "test-user-123",
                    "units": 20.0,
                    "ref": "test-ref-123",
                    "reason": "test_debit"
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["balance"] == 80.0
            assert data["tx_id"] == "tx-123"
    
    @pytest.mark.asyncio
    async def test_debit_balance_insufficient_funds(self, client, mock_user_balance):
        """Тест списания при недостаточных средствах"""
        with patch('app.services.balance_service.TransactionDAO.get_by_ref_and_direction', return_value=None), \
             patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance):
            
            response = await client.post(
                "/internal/billing/debit",
                json={
                    "user_id": "test-user-123",
                    "units": 150.0,
                    "ref": "test-ref-123",
                    "reason": "test_debit"
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 403
            data = response.json()
            assert "quota_exceeded" in str(data["detail"])
    
    @pytest.mark.asyncio
    async def test_credit_balance_success(self, client, mock_user_balance, mock_transaction):
        """Тест успешного пополнения баланса"""
        with patch('app.services.balance_service.TransactionDAO.get_by_ref_and_direction', return_value=None), \
             patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance), \
             patch('app.services.balance_service.BalanceDAO.update_balance'), \
             patch('app.services.balance_service.TransactionDAO.create_transaction', return_value=mock_transaction):
            
            response = await client.post(
                "/internal/billing/credit",
                json={
                    "user_id": "test-user-123",
                    "units": 100.0,
                    "ref": "test-ref-123",
                    "source_service": "test_service",
                    "reason": "test_credit"
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["balance"] == 200.0
            assert data["tx_id"] == "tx-123"
    
    @pytest.mark.asyncio
    async def test_get_balance_with_plan(self, client, mock_user_balance, mock_user_plan):
        """Тест получения баланса с информацией о плане"""
        with patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance), \
             patch('app.services.plan_service.PlanDAO.get_active_plan_by_user', return_value=mock_user_plan):
            
            response = await client.get(
                "/internal/billing/balance?user_id=test-user-123",
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["balance"] == 100.0
            assert data["plan"]["plan_code"] == "test_plan"
            assert data["plan"]["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_get_balance_without_plan(self, client, mock_user_balance):
        """Тест получения баланса без плана"""
        with patch('app.services.balance_service.BalanceDAO.get_or_create_balance', return_value=mock_user_balance), \
             patch('app.services.plan_service.PlanDAO.get_active_plan_by_user', return_value=None):
            
            response = await client.get(
                "/internal/billing/balance?user_id=test-user-123",
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["balance"] == 100.0
            assert data["plan"] is None
    
    @pytest.mark.asyncio
    async def test_apply_plan_success(self, client, mock_tariff_plan, mock_user_plan):
        """Тест успешного применения плана"""
        with patch('app.services.plan_service.PlanDAO.get_tariff_plan', return_value=mock_tariff_plan), \
             patch('app.services.plan_service.PlanDAO.apply_plan', return_value=mock_user_plan), \
             patch('app.services.balance_service.BalanceService.credit_balance', return_value=(500.0, "tx-123")):
            
            response = await client.post(
                "/internal/billing/plan/apply",
                json={
                    "user_id": "test-user-123",
                    "plan_code": "test_plan",
                    "ref": "test-ref-123",
                    "auto_renew": False
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["plan_id"] == "user-plan-123"
            assert data["new_balance"] == 500.0
    
    @pytest.mark.asyncio
    async def test_apply_plan_not_found(self, client):
        """Тест применения несуществующего плана"""
        with patch('app.services.plan_service.PlanDAO.get_tariff_plan', return_value=None):
            response = await client.post(
                "/internal/billing/plan/apply",
                json={
                    "user_id": "test-user-123",
                    "plan_code": "invalid_plan",
                    "ref": "test-ref-123",
                    "auto_renew": False
                },
                headers={"X-Internal-Key": "super-secret-dev"}
            )
            
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["code"] == "plan_not_found"
    
    @pytest.mark.asyncio
    async def test_invalid_internal_key(self, client):
        """Тест с неверным внутренним ключом"""
        response = await client.post(
            "/internal/billing/check",
            json={
                "user_id": "test-user-123",
                "units": 50.0
            },
            headers={"X-Internal-Key": "wrong-key"}
        )
        
        assert response.status_code == 401
        assert "Invalid internal key" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_missing_internal_key(self, client):
        """Тест без внутреннего ключа"""
        response = await client.post(
            "/internal/billing/check",
            json={
                "user_id": "test-user-123",
                "units": 50.0
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_invalid_request_data(self, client):
        """Тест с невалидными данными запроса"""
        response = await client.post(
            "/internal/billing/check",
            json={
                "user_id": "test-user-123",
                "units": -5.0  # Отрицательные единицы
            },
            headers={"X-Internal-Key": "super-secret-dev"}
        )
        
        assert response.status_code == 422  # Validation error 