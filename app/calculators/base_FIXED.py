"""
Base calculator class for payroll calculations.
"""
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple
from datetime import date

from app.models import EmployeeInput, PayrollCalculationResult, PayrollLineItem


class BasePayrollCalculator(ABC):
    """Abstract base class for jurisdiction-specific payroll calculators."""
    
    def __init__(self):
        self.line_items: List[PayrollLineItem] = []
        self.warnings: List[str] = []
        self.notes: List[str] = []
    
    def round_currency(self, amount: Decimal) -> Decimal:
        """Round to 2 decimal places for currency."""
        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def add_line_item(self, code: str, name: str, category: str, 
                     amount: Decimal, rate: Decimal = None, 
                     base_amount: Decimal = None, notes: str = None):
        """Add a calculation line item."""
        self.line_items.append(PayrollLineItem(
            code=code,
            name=name,
            category=category,
            amount=self.round_currency(amount),
            rate=rate,
            base_amount=base_amount,
            notes=notes
        ))
    
    def calculate(self, employee: EmployeeInput) -> PayrollCalculationResult:
        """
        Main calculation method.
        
        This orchestrates the calculation process:
        1. Calculate gross earnings
        2. Calculate statutory deductions (tax, social security)
        3. Calculate other deductions
        4. Calculate net salary (handling loon in natura)
        """
        self.line_items = []
        self.warnings = []
        self.notes = []
        
        # Step 1: Calculate gross (for tax calculation)
        gross_total = self.calculate_gross(employee)
        
        # Step 2: Calculate tax
        tax_amount = self.calculate_tax(employee, gross_total)
        
        # Step 3: Calculate social security
        social_security = self.calculate_social_security(employee, gross_total)
        
        # Step 4: Other deductions
        other_deductions_total = self.calculate_other_deductions(employee)
        
        # Step 5: Calculate net (handle loon in natura)
        deductions_total = tax_amount + sum(social_security.values()) + other_deductions_total
        
        # Net calculation: Start with base salary only (not total gross)
        # Loon in natura (like phone) is taxable but NOT paid out
        net_salary = employee.gross_salary  # Start with base only
        
        # Add allowances that are actually paid (exclude "phone" = loon in natura)
        for allowance_code, amount in employee.allowances.items():
            if allowance_code.lower() not in ['phone', 'telefoon']:
                net_salary += amount
        
        # Subtract deductions
        net_salary -= deductions_total
        
        # Build result
        earnings_dict = {item.code: item.amount for item in self.line_items if item.category == "EARNING"}
        statutory_dict = {item.code: item.amount for item in self.line_items 
                         if item.category == "DEDUCTION" and item.code in ['TAX', 'AOV', 'AWW', 'CESANTIA', 'SOCIAL_SEC']}
        other_dict = {item.code: item.amount for item in self.line_items 
                     if item.category == "DEDUCTION" and item.code not in ['TAX', 'AOV', 'AWW', 'CESANTIA', 'SOCIAL_SEC']}
        
        return PayrollCalculationResult(
            employee_id=employee.employee_id,
            jurisdiction=employee.jurisdiction,
            period_start=employee.period_start,
            period_end=employee.period_end,
            gross_total=self.round_currency(gross_total),
            deductions_total=self.round_currency(deductions_total),
            net_salary=self.round_currency(net_salary),
            line_items=self.line_items,
            earnings=earnings_dict,
            statutory_deductions=statutory_dict,
            other_deductions=other_dict,
            calculation_notes=self.notes,
            warnings=self.warnings
        )
    
    @abstractmethod
    def calculate_gross(self, employee: EmployeeInput) -> Decimal:
        """Calculate total gross earnings."""
        pass
    
    @abstractmethod
    def calculate_tax(self, employee: EmployeeInput, gross: Decimal) -> Decimal:
        """Calculate income/wage tax."""
        pass
    
    @abstractmethod
    def calculate_social_security(self, employee: EmployeeInput, gross: Decimal) -> Dict[str, Decimal]:
        """Calculate social security contributions."""
        pass
    
    def calculate_other_deductions(self, employee: EmployeeInput) -> Decimal:
        """Calculate other (non-statutory) deductions."""
        total = Decimal("0")
        
        for code, amount in employee.deductions.items():
            self.add_line_item(
                code=f"DED_{code.upper()}",
                name=code.replace('_', ' ').title(),
                category="DEDUCTION",
                amount=amount
            )
            total += amount
        
        return total
    
    def calculate_progressive_tax(self, taxable_amount: Decimal, 
                                 brackets: List[Tuple[Decimal, Decimal, Decimal]]) -> Tuple[Decimal, str]:
        """
        Calculate tax using progressive brackets.
        
        Args:
            taxable_amount: The amount to tax
            brackets: List of (lower_limit, upper_limit, rate) tuples
        
        Returns:
            Tuple of (tax_amount, calculation_notes)
        """
        tax = Decimal("0")
        notes_parts = []
        
        for lower, upper, rate in brackets:
            if taxable_amount <= lower:
                break
            
            bracket_amount = min(taxable_amount, upper) - lower
            bracket_tax = bracket_amount * rate
            tax += bracket_tax
            
            notes_parts.append(f"{rate * 100}% on {bracket_amount}")
        
        notes = " + ".join(notes_parts) if notes_parts else "No tax"
        return self.round_currency(tax), notes
