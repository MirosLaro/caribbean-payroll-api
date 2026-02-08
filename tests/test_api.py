"""
Tests for Caribbean Payroll API
"""
import pytest
from fastapi.testclient import TestClient
from datetime import date
from decimal import Decimal

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "curacao" in data["jurisdictions_available"]


class TestCuracaoCalculation:
    """Test Curaçao payroll calculations"""
    
    def test_basic_salary_calculation(self):
        """Test simple salary calculation without extras"""
        request_data = {
            "employee_id": "TEST001",
            "name": "Test Employee",
            "jurisdiction": "curacao",
            "gross_salary": 4000.00,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["employee_id"] == "TEST001"
        assert data["gross_total"] == 4000.00
        assert data["net_salary"] > 0
        assert data["net_salary"] < data["gross_total"]
        
        # Check for expected line items
        line_codes = [item["code"] for item in data["line_items"]]
        assert "BASIC" in line_codes
        assert "TAX" in line_codes
        assert "AOV" in line_codes
        assert "AWW" in line_codes
        assert "CESANTIA" in line_codes
    
    def test_with_overtime(self):
        """Test calculation with overtime hours"""
        request_data = {
            "employee_id": "TEST002",
            "name": "Test Employee 2",
            "jurisdiction": "curacao",
            "gross_salary": 5000.00,
            "hourly_rate": 31.25,
            "overtime_hours": 10.0,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Gross should include overtime
        assert data["gross_total"] > 5000.00
        
        # Check for overtime line
        overtime_lines = [item for item in data["line_items"] if item["code"] == "OVERTIME"]
        assert len(overtime_lines) == 1
        assert overtime_lines[0]["amount"] > 0
    
    def test_with_allowances(self):
        """Test calculation with allowances"""
        request_data = {
            "employee_id": "TEST003",
            "name": "Test Employee 3",
            "jurisdiction": "curacao",
            "gross_salary": 4500.00,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
            "allowances": {
                "transportation": 200.00,
                "meal": 150.00
            }
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        # Gross should include allowances
        assert data["gross_total"] == 4850.00
        
        # Check for allowance lines
        allowance_lines = [item for item in data["line_items"] if "ALW_" in item["code"]]
        assert len(allowance_lines) == 2
    
    def test_tax_brackets(self):
        """Test progressive tax calculation"""
        # Test with salary in different brackets
        salaries = [2000.00, 4000.00, 6000.00, 12000.00]
        
        for salary in salaries:
            request_data = {
                "employee_id": f"TEST_{salary}",
                "name": f"Test {salary}",
                "jurisdiction": "curacao",
                "gross_salary": salary,
                "period_start": "2025-02-01",
                "period_end": "2025-02-28",
            }
            
            response = client.post("/api/v1/calculate/curacao", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            tax_line = next(item for item in data["line_items"] if item["code"] == "TAX")
            
            # Tax should increase with salary but not linearly
            assert tax_line["amount"] > 0
            assert tax_line["amount"] < data["gross_total"]
    
    def test_aov_cap(self):
        """Test that AOV is capped at maximum base"""
        # High salary should still have capped AOV
        request_data = {
            "employee_id": "TEST_HIGH",
            "name": "High Earner",
            "jurisdiction": "curacao",
            "gross_salary": 10000.00,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        aov_line = next(item for item in data["line_items"] if item["code"] == "AOV")
        
        # AOV should be capped: 7% of 5000 = 350
        assert aov_line["amount"] == 350.00
        assert aov_line["base_amount"] == 5000.00
    
    def test_tax_exempt(self):
        """Test tax-exempt employee"""
        request_data = {
            "employee_id": "TEST_EXEMPT",
            "name": "Exempt Employee",
            "jurisdiction": "curacao",
            "gross_salary": 4000.00,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
            "tax_exempt": True
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        tax_line = next(item for item in data["line_items"] if item["code"] == "TAX")
        
        assert tax_line["amount"] == 0
        assert "exempt" in tax_line["notes"].lower()


class TestBatchCalculation:
    """Test batch calculation endpoint"""
    
    def test_batch_calculation(self):
        """Test calculating multiple employees"""
        request_data = {
            "employees": [
                {
                    "employee_id": "BATCH001",
                    "name": "Batch Employee 1",
                    "jurisdiction": "curacao",
                    "gross_salary": 3000.00,
                    "period_start": "2025-02-01",
                    "period_end": "2025-02-28",
                },
                {
                    "employee_id": "BATCH002",
                    "name": "Batch Employee 2",
                    "jurisdiction": "st_maarten",
                    "gross_salary": 3500.00,
                    "period_start": "2025-02-01",
                    "period_end": "2025-02-28",
                }
            ]
        }
        
        response = client.post("/api/v1/calculate/batch", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        assert len(data["results"]) == 2


class TestErrorHandling:
    """Test error handling and validation"""
    
    def test_invalid_jurisdiction(self):
        """Test with invalid jurisdiction"""
        request_data = {
            "employee_id": "TEST_INVALID",
            "name": "Invalid Employee",
            "jurisdiction": "invalid_place",
            "gross_salary": 4000.00,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
        }
        
        response = client.post("/api/v1/calculate/invalid_place", json=request_data)
        assert response.status_code == 400
    
    def test_missing_required_fields(self):
        """Test with missing required fields"""
        request_data = {
            "employee_id": "TEST_MISSING",
            "jurisdiction": "curacao",
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_negative_salary(self):
        """Test with negative salary"""
        request_data = {
            "employee_id": "TEST_NEG",
            "name": "Negative Employee",
            "jurisdiction": "curacao",
            "gross_salary": -1000.00,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28",
        }
        
        response = client.post("/api/v1/calculate/curacao", json=request_data)
        assert response.status_code == 422


class TestJurisdictions:
    """Test jurisdiction listing"""
    
    def test_list_jurisdictions(self):
        """Test listing all jurisdictions"""
        response = client.get("/api/v1/jurisdictions")
        assert response.status_code == 200
        
        data = response.json()
        assert "jurisdictions" in data
        assert len(data["jurisdictions"]) == 4
        
        codes = [j["code"] for j in data["jurisdictions"]]
        assert "curacao" in codes
        assert "st_maarten" in codes
        assert "aruba" in codes
        assert "bonaire" in codes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
