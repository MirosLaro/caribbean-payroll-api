"""
Bonaire Payroll Calculator

TODO: Implement Bonaire-specific tax and social security calculations.
"""
from decimal import Decimal
from typing import Dict

from app.models import EmployeeInput
from app.calculators.base import BasePayrollCalculator


class BonaireCalculator(BasePayrollCalculator):
    """Payroll calculator for Bonaire jurisdiction."""
    
    # TODO: Add actual Bonaire tax brackets
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("2800"), Decimal("0.15")),
        (Decimal("2800"), Decimal("999999999"), Decimal("0.40")),
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
        """Calculate Bonaire payroll tax."""
        tax, notes = self.calculate_progressive_tax(gross, self.TAX_BRACKETS)
        
        self.add_line_item(
            code="TAX",
            name="Payroll Tax",
            category="DEDUCTION",
            amount=tax,
            base_amount=gross,
            notes=notes
        )
        
        return tax
    
    def calculate_social_security(self, employee: EmployeeInput, gross: Decimal) -> Dict[str, Decimal]:
        """Calculate Bonaire social insurance."""
        # TODO: Implement social insurance for Bonaire
        return {}


bonaire_calculator = BonaireCalculator()
