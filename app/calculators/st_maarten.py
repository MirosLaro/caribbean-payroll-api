"""
St. Maarten Payroll Calculator

Implements income tax and social security calculations for St. Maarten.
TODO: Add actual St. Maarten tax brackets and social security rates.
"""
from decimal import Decimal
from typing import Dict

from app.models import EmployeeInput
from app.calculators.base import BasePayrollCalculator


class StMaartenCalculator(BasePayrollCalculator):
    """Payroll calculator for St. Maarten jurisdiction."""
    
    # TODO: Update with actual St. Maarten tax brackets
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("2500"), Decimal("0.10")),
        (Decimal("2500"), Decimal("5000"), Decimal("0.25")),
        (Decimal("5000"), Decimal("999999999"), Decimal("0.45")),
    ]
    
    # TODO: Update with actual social security rates
    SOCIAL_SECURITY_RATE = Decimal("0.065")  # 6.5% example
    SOCIAL_SECURITY_MAX = Decimal("4500")
    
    def calculate_gross(self, employee: EmployeeInput) -> Decimal:
        """Calculate total gross earnings."""
        gross = employee.gross_salary
        
        self.add_line_item(
            code="BASIC",
            name="Basic Salary",
            category="EARNING",
            amount=gross
        )
        
        # Add allowances
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
        """Calculate St. Maarten income tax."""
        if employee.tax_exempt:
            self.add_line_item(
                code="TAX",
                name="Income Tax (Exempt)",
                category="DEDUCTION",
                amount=Decimal("0")
            )
            return Decimal("0")
        
        tax, notes = self.calculate_progressive_tax(gross, self.TAX_BRACKETS)
        
        self.add_line_item(
            code="TAX",
            name="Income Tax",
            category="DEDUCTION",
            amount=tax,
            base_amount=gross,
            notes=notes
        )
        
        return tax
    
    def calculate_social_security(self, employee: EmployeeInput, gross: Decimal) -> Dict[str, Decimal]:
        """Calculate St. Maarten social security."""
        contributions = {}
        
        ss_base = min(gross, self.SOCIAL_SECURITY_MAX)
        ss_amount = ss_base * self.SOCIAL_SECURITY_RATE
        
        self.add_line_item(
            code="SOCIAL_SEC",
            name="Social Security",
            category="DEDUCTION",
            amount=ss_amount,
            rate=self.SOCIAL_SECURITY_RATE,
            base_amount=ss_base
        )
        
        contributions['SOCIAL_SEC'] = ss_amount
        return contributions


st_maarten_calculator = StMaartenCalculator()
