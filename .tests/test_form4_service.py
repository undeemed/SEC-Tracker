"""
Tests for Form 4 Service and API Endpoints
"""
import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.fixture
def sample_form4_response():
    """Sample Form 4 API response data."""
    return {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
        "transactions": [
            {
                "date": "2025-01-15",
                "owner_name": "Tim Cook",
                "role": "CEO",
                "transaction_type": "sell",
                "is_planned": True,
                "shares": 50000,
                "price": 185.50,
                "amount": 9275000.0,
                "accession_number": "0001234567-25-000001"
            },
            {
                "date": "2025-01-10",
                "owner_name": "Luca Maestri",
                "role": "CFO",
                "transaction_type": "buy",
                "is_planned": False,
                "shares": 10000,
                "price": 180.00,
                "amount": 1800000.0,
                "accession_number": "0001234567-25-000002"
            }
        ],
        "summary": {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "total_buys": 1800000.0,
            "total_sells": 9275000.0,
            "net": -7475000.0,
            "buy_count": 1,
            "sell_count": 1,
            "period_days": 30,
            "last_updated": "2025-01-20T10:00:00Z"
        },
        "last_updated": "2025-01-20T10:00:00Z",
        "cache_hit": False
    }


class TestForm4Schemas:
    """Tests for Form 4 Pydantic schemas."""
    
    def test_form4_transaction(self):
        """Test Form4Transaction schema."""
        from schemas.form4 import Form4Transaction
        
        trans = Form4Transaction(
            date=date(2025, 1, 15),
            owner_name="Tim Cook",
            role="CEO",
            transaction_type="sell",
            is_planned=True,
            shares=50000,
            price=185.50,
            amount=9275000.0
        )
        
        assert trans.owner_name == "Tim Cook"
        assert trans.transaction_type == "sell"
        assert trans.amount == 9275000.0
    
    def test_form4_summary(self):
        """Test Form4Summary schema."""
        from schemas.form4 import Form4Summary
        
        summary = Form4Summary(
            ticker="AAPL",
            company_name="Apple Inc.",
            total_buys=5000000.0,
            total_sells=9275000.0,
            net=-4275000.0,
            buy_count=2,
            sell_count=1,
            period_days=30,
            last_updated=datetime.utcnow()
        )
        
        assert summary.ticker == "AAPL"
        assert summary.net == -4275000.0
        assert summary.buy_count == 2
    
    def test_form4_response(self):
        """Test complete Form4Response schema."""
        from schemas.form4 import Form4Response, Form4Transaction, Form4Summary
        
        trans = Form4Transaction(
            date=date(2025, 1, 15),
            owner_name="Tim Cook",
            transaction_type="sell",
            is_planned=True,
            shares=50000,
            price=185.50,
            amount=9275000.0
        )
        
        summary = Form4Summary(
            ticker="AAPL",
            total_buys=0,
            total_sells=9275000.0,
            net=-9275000.0,
            buy_count=0,
            sell_count=1,
            period_days=30,
            last_updated=datetime.utcnow()
        )
        
        response = Form4Response(
            ticker="AAPL",
            company_name="Apple Inc.",
            cik="0000320193",
            transactions=[trans],
            summary=summary,
            last_updated=datetime.utcnow(),
            cache_hit=False
        )
        
        assert response.ticker == "AAPL"
        assert len(response.transactions) == 1
        assert response.summary.net == -9275000.0
    
    def test_market_company_activity(self):
        """Test MarketCompanyActivity schema."""
        from schemas.form4 import MarketCompanyActivity
        
        activity = MarketCompanyActivity(
            ticker="NVDA",
            company_name="NVIDIA CORP",
            date_range="01/15/25 - 01/18/25",
            buy_count=3,
            sell_count=1,
            total_buys=5000000.0,
            total_sells=1000000.0,
            net=4000000.0,
            signal="↑",
            top_insiders=["Jensen Huang", "Colette Kress"]
        )
        
        assert activity.ticker == "NVDA"
        assert activity.signal == "↑"
        assert len(activity.top_insiders) == 2


class TestForm4Service:
    """Tests for Form4Service."""
    
    @pytest.mark.asyncio
    async def test_get_company_transactions_cache_hit(self):
        """Test getting company transactions with cache hit."""
        from services.form4_service import Form4Service
        
        with patch('services.form4_service.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value={
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "cik": "0000320193",
                "transactions": [],
                "summary": {
                    "ticker": "AAPL",
                    "total_buys": 0,
                    "total_sells": 0,
                    "net": 0,
                    "buy_count": 0,
                    "sell_count": 0,
                    "period_days": 30,
                    "last_updated": "2025-01-20T10:00:00"
                },
                "last_updated": "2025-01-20T10:00:00"
            })
            
            service = Form4Service()
            result = await service.get_company_transactions("AAPL")
            
            assert result.ticker == "AAPL"
            assert result.cache_hit is True
    
    @pytest.mark.asyncio
    async def test_get_company_summary(self):
        """Test getting company summary."""
        from services.form4_service import Form4Service
        
        with patch.object(Form4Service, 'get_company_transactions') as mock_get:
            from schemas.form4 import Form4Response, Form4Summary
            
            mock_response = MagicMock(spec=Form4Response)
            mock_response.summary = Form4Summary(
                ticker="NVDA",
                total_buys=10000000,
                total_sells=2000000,
                net=8000000,
                buy_count=5,
                sell_count=2,
                period_days=30,
                last_updated=datetime.utcnow()
            )
            mock_get.return_value = mock_response
            
            service = Form4Service()
            summary = await service.get_company_summary("NVDA", days_back=30)
            
            assert summary.ticker == "NVDA"
            assert summary.net == 8000000


class TestForm4Transaction:
    """Tests for Form 4 transaction parsing."""
    
    def test_transaction_type_buy(self):
        """Test buy transaction detection."""
        from schemas.form4 import Form4Transaction
        
        trans = Form4Transaction(
            date=date(2025, 1, 15),
            owner_name="Test User",
            transaction_type="buy",
            shares=1000,
            price=100.0,
            amount=100000.0
        )
        
        assert trans.transaction_type == "buy"
    
    def test_transaction_type_sell(self):
        """Test sell transaction detection."""
        from schemas.form4 import Form4Transaction
        
        trans = Form4Transaction(
            date=date(2025, 1, 15),
            owner_name="Test User",
            transaction_type="sell",
            shares=1000,
            price=100.0,
            amount=100000.0
        )
        
        assert trans.transaction_type == "sell"
    
    def test_transaction_planned(self):
        """Test 10b5-1 planned transaction flag."""
        from schemas.form4 import Form4Transaction
        
        trans = Form4Transaction(
            date=date(2025, 1, 15),
            owner_name="Test User",
            transaction_type="sell",
            is_planned=True,
            shares=1000,
            price=100.0,
            amount=100000.0
        )
        
        assert trans.is_planned is True
    
    def test_transaction_amount_calculation(self):
        """Test transaction amount matches shares * price."""
        from schemas.form4 import Form4Transaction
        
        shares = 1000.0
        price = 150.50
        expected_amount = shares * price
        
        trans = Form4Transaction(
            date=date(2025, 1, 15),
            owner_name="Test User",
            transaction_type="buy",
            shares=shares,
            price=price,
            amount=expected_amount
        )
        
        assert trans.amount == expected_amount
