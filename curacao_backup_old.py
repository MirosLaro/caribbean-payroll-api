"""
Curaçao Payroll Calculator

Implements wage tax (loonbelasting), AOV, AWW, and Cesantia calculations
according to Curaçao tax laws.
"""
from decimal import Decimal
from typing import Dict, List, Tuple

from app.models import EmployeeInput
from app.calculators.base import BasePayrollCalculator


class CuracaoCalculator(BasePayrollCalculator):
    """Payroll calculator for Curaçao jurisdiction."""
    
    # 2024/2025 Wage Tax Brackets (monthly)
    # These are example brackets - update with actual current rates
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("3333"), Decimal("0.14")),           # 14% up to ANG 3,333
        (Decimal("3333"), Decimal("5000"), Decimal("0.25")),        # 25% from 3,333 to 5,000
        (Decimal("5000"), Decimal("10000"), Decimal("0.40")),       # 40% from 5,000 to 10,000
        (Decimal("10000"), Decimal("999999999"), Decimal("0.47")),  # 47% above 10,000
    ]
    
    # AOV (Old Age Pension) - 2024/2025
    AOV_RATE = Decimal("0.07")  # 7% employee contribution
    AOV_MAX_BASE = Decimal("5000")  # Maximum base for AOV calculation
    
    # AWW (Widow/Widower Insurance)
    AWW_RATE = Decimal("0.01")  # 1% employee contribution
    AWW_MAX_BASE = Decimal("5000")  # Maximum base for AWW calculation
    
    # Cesantia (Unemployment Insurance)
    CESANTIA_RATE = Decimal("0.01")  # 1% employee contribution
    
    # Overtime multiplier
    OVERTIME_MULTIPLIER = Decimal("1.5")
    
    def calculate_gross(self, employee: EmployeeInput) -> Decimal:
        """
        Calculate total gross earnings including base salary, overtime, and allowances.
        """
        gross = Decimal("0")
        
        # Base salary
        base_salary = employee.gross_salary
        self.add_line_item(
            code="BASIC",
            name="Basic Salary",
            category="EARNING",
            amount=base_salary
        )
        gross += base_salary
        
        # Overtime calculation
        if employee.overtime_hours > 0:
            if employee.hourly_rate:
                overtime_rate = employee.hourly_rate * self.OVERTIME_MULTIPLIER
            else:
                # Calculate hourly rate from monthly salary
                # Assuming 160 hours/month standard
                standard_hours = Decimal("160")
                calculated_hourly_rate = employee.gross_salary / standard_hours
                overtime_rate = calculated_hourly_rate * self.OVERTIME_MULTIPLIER
            
            overtime_pay = overtime_rate * employee.overtime_hours
            
            self.add_line_item(
                code="OVERTIME",
                name="Overtime Pay",
                category="EARNING",
                amount=overtime_pay,
                rate=self.OVERTIME_MULTIPLIER,
                base_amount=overtime_rate,
                notes=f"{employee.overtime_hours} hours @ {overtime_rate}/hour"
            )
            gross += overtime_pay
        
        # Allowances
        for allowance_code, amount in employee.allowances.items():
            self.add_line_item(
                code=f"ALW_{allowance_code.upper()}",
                name=allowance_code.replace('_', ' ').title(),
                category="EARNING",
                amount=amount
            )
            gross += amount
        
        return gross
    
    def calculate_tax(self, employee: EmployeeInput, gross: Decimal) -> Decimal:
        """
        Calculate Curaçao wage tax (loonbelasting) using progressive brackets.
        """
        if employee.tax_exempt:
            self.warnings.append("Employee is tax exempt")
            self.add_line_item(
                code="TAX",
                name="Wage Tax (Exempt)",
                category="DEDUCTION",
                amount=Decimal("0"),
                notes="Tax exempt status"
            )
            return Decimal("0")
        
        # If custom tax percentage is specified
        if employee.tax_percentage is not None:
            tax = gross * (employee.tax_percentage / Decimal("100"))
            self.add_line_item(
                code="TAX",
                name="Wage Tax",
                category="DEDUCTION",
                amount=tax,
                rate=employee.tax_percentage / Decimal("100"),
                base_amount=gross,
                notes=f"Custom rate: {employee.tax_percentage}%"
            )
            return tax
        
        # Standard progressive tax calculation
        tax, tax_notes = self.calculate_progressive_tax(gross, self.TAX_BRACKETS)
        
        self.add_line_item(
            code="TAX",
            name="Wage Tax (Loonbelasting)",
            category="DEDUCTION",
            amount=tax,
            base_amount=gross,
            notes=tax_notes
        )
        
        return tax
    
    def calculate_social_security(self, employee: EmployeeInput, gross: Decimal) -> Dict[str, Decimal]:
        """
        Calculate Curaçao social security contributions (AOV, AWW, Cesantia).
        """
        contributions = {}
        
        # AOV (Old Age Pension)
        if not employee.aov_exempt:
            aov_base = min(gross, self.AOV_MAX_BASE)
            aov_amount = aov_base * self.AOV_RATE
            
            self.add_line_item(
                code="AOV",
                name="AOV (Old Age Pension)",
                category="DEDUCTION",
                amount=aov_amount,
                rate=self.AOV_RATE,
                base_amount=aov_base,
                notes=f"{self.AOV_RATE * 100}% on max {self.AOV_MAX_BASE}"
            )
            contributions['AOV'] = aov_amount
        else:
            self.warnings.append("Employee is AOV exempt")
            contributions['AOV'] = Decimal("0")
        
        # AWW (Widow/Widower Insurance)
        if not employee.aww_exempt:
            aww_base = min(gross, self.AWW_MAX_BASE)
            aww_amount = aww_base * self.AWW_RATE
            
            self.add_line_item(
                code="AWW",
                name="AWW (Widow/Widower Insurance)",
                category="DEDUCTION",
                amount=aww_amount,
                rate=self.AWW_RATE,
                base_amount=aww_base,
                notes=f"{self.AWW_RATE * 100}% on max {self.AWW_MAX_BASE}"
            )
            contributions['AWW'] = aww_amount
        else:
            self.warnings.append("Employee is AWW exempt")
            contributions['AWW'] = Decimal("0")
        
        # Cesantia (Unemployment Insurance)
        # Usually calculated on full gross without cap
        cesantia_amount = gross * self.CESANTIA_RATE
        
        self.add_line_item(
            code="CESANTIA",
            name="Cesantia (Unemployment)",
            category="DEDUCTION",
            amount=cesantia_amount,
            rate=self.CESANTIA_RATE,
            base_amount=gross,
            notes=f"{self.CESANTIA_RATE * 100}% on gross"
        )
        contributions['CESANTIA'] = cesantia_amount
        
        return contributions


# Create singleton instance
curacao_calculator = CuracaoCalculator()
