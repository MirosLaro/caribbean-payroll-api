"""
Data models for payroll calculation API.
"""
from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, validator


class EmployeeInput(BaseModel):
    """Employee information for payroll calculation."""
    
    employee_id: str = Field(..., description="Unique employee identifier")
    name: str = Field(..., description="Employee full name")
    jurisdiction: str = Field(..., description="curacao, st_maarten, aruba, or bonaire")
    
    # Salary information
    gross_salary: Decimal = Field(..., gt=0, description="Monthly gross salary")
    hourly_rate: Optional[Decimal] = Field(None, description="Hourly rate if applicable")
    
    # Work period
    period_start: date = Field(..., description="Payroll period start date")
    period_end: date = Field(..., description="Payroll period end date")
    
    # Additional inputs
    regular_hours: Decimal = Field(default=Decimal("160"), description="Regular working hours")
    overtime_hours: Decimal = Field(default=Decimal("0"), description="Overtime hours")
    
    # Allowances
    allowances: Dict[str, Decimal] = Field(default_factory=dict, description="Various allowances")
    
    # Deductions (non-statutory)
    deductions: Dict[str, Decimal] = Field(default_factory=dict, description="Additional deductions")
    
    # Employee-specific data
    tax_exempt: bool = Field(default=False, description="Tax exemption status")
    tax_percentage: Optional[Decimal] = Field(None, description="Custom tax percentage if applicable")
    dependents: int = Field(default=0, description="Number of dependents")
    
    # Social security
    aov_exempt: bool = Field(default=False, description="AOV exemption")
    aww_exempt: bool = Field(default=False, description="AWW exemption")
    
    @validator('jurisdiction')
    def validate_jurisdiction(cls, v):
        valid = ['curacao', 'st_maarten', 'aruba', 'bonaire']
        if v.lower() not in valid:
            raise ValueError(f'Jurisdiction must be one of {valid}')
        return v.lower()


class PayrollLineItem(BaseModel):
    """Single line item in payroll calculation."""
    
    code: str = Field(..., description="Rule code (e.g., GROSS, TAX, AOV)")
    name: str = Field(..., description="Display name")
    category: str = Field(..., description="EARNING, DEDUCTION, or NET")
    amount: Decimal = Field(..., description="Calculated amount")
    rate: Optional[Decimal] = Field(None, description="Applied rate/percentage")
    base_amount: Optional[Decimal] = Field(None, description="Base amount for calculation")
    notes: Optional[str] = Field(None, description="Additional notes or details")


class PayrollCalculationResult(BaseModel):
    """Complete payroll calculation result."""
    
    employee_id: str
    jurisdiction: str
    period_start: date
    period_end: date
    
    # Summary amounts
    gross_total: Decimal = Field(..., description="Total gross earnings")
    deductions_total: Decimal = Field(..., description="Total deductions")
    net_salary: Decimal = Field(..., description="Net pay amount")
    
    # Detailed line items
    line_items: List[PayrollLineItem] = Field(..., description="All calculation line items")
    
    # Breakdown by category
    earnings: Dict[str, Decimal] = Field(default_factory=dict)
    statutory_deductions: Dict[str, Decimal] = Field(default_factory=dict)
    other_deductions: Dict[str, Decimal] = Field(default_factory=dict)
    
    # Metadata
    calculation_date: date = Field(default_factory=date.today)
    calculation_notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BatchCalculationRequest(BaseModel):
    """Request for batch payroll calculation."""
    
    employees: List[EmployeeInput] = Field(..., description="List of employees to calculate")
    validate_only: bool = Field(default=False, description="Only validate without calculating")


class BatchCalculationResponse(BaseModel):
    """Response for batch calculation."""
    
    success_count: int
    error_count: int
    results: List[PayrollCalculationResult]
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = "healthy"
    version: str = "1.0.0"
    jurisdictions_available: List[str] = ["curacao", "st_maarten", "aruba", "bonaire"]
