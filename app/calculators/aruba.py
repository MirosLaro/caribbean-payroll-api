"""
Aruba Payroll Calculator

TODO: Implement Aruba-specific tax and social security calculations.
"""
from decimal import Decimal
from typing import Dict

from app.models import EmployeeInput
from app.calculators.base import BasePayrollCalculator


class ArubaCalculator(BasePayrollCalculator):
    """Payroll calculator for Aruba jurisdiction."""
    
    # TODO: Add actual Aruba tax brackets
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("3000"), Decimal("0.12")),
        (Decimal("3000"), Decimal("999999999"), Decimal("0.45")),
    ]
    
    def calculate_gross(self, employee: EmployeeInput) -> Decimal:
        """Calculate total gross earnings."""
        gross = employee.gross_salary
        
        self.add_line_item(
            code="BASIC",
            name="Basic Salary",
            category="EARNING",
            amount=gross
        )
        
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
        """Calculate Aruba income tax."""
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
        """Calculate Aruba social security."""
        # TODO: Implement AOV, AWW for Aruba
        return {}


aruba_calculator = ArubaCalculator()
