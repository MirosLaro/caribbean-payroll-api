#!/usr/bin/env python3
"""
Example usage of the Caribbean Payroll API

This script demonstrates how to:
1. Calculate payroll for a single employee
2. Process a batch of employees
3. Handle different scenarios (overtime, allowances, etc.)
"""

import requests
import json
from datetime import date, timedelta
from decimal import Decimal


API_URL = "http://localhost:8000"  # Change to your API URL


def calculate_single_employee():
    """Example: Calculate payroll for a single employee"""
    print("\n=== Single Employee Calculation ===\n")
    
    employee_data = {
        "employee_id": "EMP001",
        "name": "Maria Gonzalez",
        "jurisdiction": "curacao",
        "gross_salary": 4500.00,
        "period_start": "2025-02-01",
        "period_end": "2025-02-28",
        "regular_hours": 160,
        "overtime_hours": 8,
        "allowances": {
            "transportation": 200.00,
            "meal": 150.00
        }
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/calculate/curacao",
        json=employee_data
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"Employee: {result['employee_id']}")
        print(f"Gross Total: ANG {result['gross_total']:.2f}")
        print(f"Deductions: ANG {result['deductions_total']:.2f}")
        print(f"Net Salary: ANG {result['net_salary']:.2f}")
        print("\nLine Items:")
        
        for item in result['line_items']:
            category_symbol = "+" if item['category'] == "EARNING" else "-"
            print(f"  {category_symbol} {item['name']}: ANG {item['amount']:.2f}")
        
        if result.get('warnings'):
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")
        
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.json())
        return None


def calculate_with_overtime():
    """Example: Employee with significant overtime"""
    print("\n=== Overtime Calculation ===\n")
    
    employee_data = {
        "employee_id": "EMP002",
        "name": "Carlos Hernandez",
        "jurisdiction": "curacao",
        "gross_salary": 3500.00,
        "hourly_rate": 21.875,  # 3500 / 160 hours
        "period_start": "2025-02-01",
        "period_end": "2025-02-28",
        "regular_hours": 160,
        "overtime_hours": 20  # Significant overtime
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/calculate/curacao",
        json=employee_data
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"Employee: {result['employee_id']}")
        print(f"Base Salary: ANG 3,500.00")
        print(f"Overtime: ANG {result['earnings'].get('OVERTIME', 0):.2f}")
        print(f"Gross Total: ANG {result['gross_total']:.2f}")
        print(f"Net Salary: ANG {result['net_salary']:.2f}")
        
        return result
    else:
        print(f"Error: {response.status_code}")
        return None


def calculate_tax_exempt():
    """Example: Tax-exempt employee"""
    print("\n=== Tax-Exempt Employee ===\n")
    
    employee_data = {
        "employee_id": "EMP003",
        "name": "Ana Martinez",
        "jurisdiction": "curacao",
        "gross_salary": 5000.00,
        "period_start": "2025-02-01",
        "period_end": "2025-02-28",
        "tax_exempt": True
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/calculate/curacao",
        json=employee_data
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"Employee: {result['employee_id']}")
        print(f"Gross: ANG {result['gross_total']:.2f}")
        print(f"Tax: ANG {result['statutory_deductions'].get('TAX', 0):.2f} (EXEMPT)")
        print(f"Net: ANG {result['net_salary']:.2f}")
        
        return result
    else:
        print(f"Error: {response.status_code}")
        return None


def batch_calculation():
    """Example: Calculate multiple employees at once"""
    print("\n=== Batch Calculation ===\n")
    
    employees = [
        {
            "employee_id": f"BATCH{i:03d}",
            "name": f"Employee {i}",
            "jurisdiction": "curacao",
            "gross_salary": 3000 + (i * 100),
            "period_start": "2025-02-01",
            "period_end": "2025-02-28"
        }
        for i in range(1, 11)  # 10 employees
    ]
    
    response = requests.post(
        f"{API_URL}/api/v1/calculate/batch",
        json={"employees": employees}
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print(f"Successfully calculated: {result['success_count']}")
        print(f"Errors: {result['error_count']}")
        
        if result['results']:
            print("\nSummary:")
            total_gross = sum(r['gross_total'] for r in result['results'])
            total_net = sum(r['net_salary'] for r in result['results'])
            total_tax = sum(r['statutory_deductions'].get('TAX', 0) for r in result['results'])
            
            print(f"  Total Gross: ANG {total_gross:.2f}")
            print(f"  Total Tax: ANG {total_tax:.2f}")
            print(f"  Total Net: ANG {total_net:.2f}")
        
        return result
    else:
        print(f"Error: {response.status_code}")
        return None


def compare_jurisdictions():
    """Example: Compare same salary across different jurisdictions"""
    print("\n=== Jurisdiction Comparison ===\n")
    
    base_salary = 4000.00
    jurisdictions = ["curacao", "st_maarten", "aruba", "bonaire"]
    
    results = {}
    
    for jurisdiction in jurisdictions:
        employee_data = {
            "employee_id": f"COMP_{jurisdiction.upper()}",
            "name": f"Employee {jurisdiction}",
            "jurisdiction": jurisdiction,
            "gross_salary": base_salary,
            "period_start": "2025-02-01",
            "period_end": "2025-02-28"
        }
        
        response = requests.post(
            f"{API_URL}/api/v1/calculate/{jurisdiction}",
            json=employee_data
        )
        
        if response.status_code == 200:
            result = response.json()
            results[jurisdiction] = result
    
    print(f"Gross Salary: ANG {base_salary:.2f}\n")
    print(f"{'Jurisdiction':<15} {'Tax':<12} {'Deductions':<12} {'Net':<12}")
    print("-" * 55)
    
    for jurisdiction, result in results.items():
        tax = result['statutory_deductions'].get('TAX', 0)
        deductions = result['deductions_total']
        net = result['net_salary']
        
        print(f"{jurisdiction.title():<15} "
              f"ANG {tax:<8.2f} "
              f"ANG {deductions:<8.2f} "
              f"ANG {net:<8.2f}")
    
    return results


def health_check():
    """Check if API is healthy"""
    print("\n=== API Health Check ===\n")
    
    response = requests.get(f"{API_URL}/api/v1/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Version: {data['version']}")
        print(f"Available Jurisdictions: {', '.join(data['jurisdictions_available'])}")
        return True
    else:
        print(f"API is not healthy! Status code: {response.status_code}")
        return False


def main():
    """Run all examples"""
    print("=" * 60)
    print("Caribbean Payroll API - Usage Examples")
    print("=" * 60)
    
    # Check API health first
    if not health_check():
        print("\n⚠ API is not available. Please start the API server first.")
        print("Run: cd api && uvicorn app.main:app --reload")
        return
    
    try:
        # Run examples
        calculate_single_employee()
        calculate_with_overtime()
        calculate_tax_exempt()
        batch_calculation()
        compare_jurisdictions()
        
        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n⚠ Cannot connect to API. Make sure it's running at:", API_URL)
    except Exception as e:
        print(f"\n⚠ Error: {e}")


if __name__ == "__main__":
    main()
