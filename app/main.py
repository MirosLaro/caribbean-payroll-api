"""
Caribbean Payroll Calculation API

FastAPI application providing payroll calculation services for
Curaçao, St. Maarten, Aruba, and Bonaire.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

from app.models import (
    EmployeeInput,
    PayrollCalculationResult,
    BatchCalculationRequest,
    BatchCalculationResponse,
    HealthResponse
)
from app.calculators.curacao import curacao_calculator
from app.calculators.st_maarten import st_maarten_calculator
from app.calculators.aruba import aruba_calculator
from app.calculators.bonaire import bonaire_calculator


app = FastAPI(
    title="Caribbean Payroll Calculation API",
    description="Payroll calculation service for Caribbean jurisdictions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Odoo integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Calculator registry
CALCULATORS = {
    "curacao": curacao_calculator,
    "st_maarten": st_maarten_calculator,
    "aruba": aruba_calculator,
    "bonaire": bonaire_calculator,
}


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint."""
    return {
        "message": "Caribbean Payroll Calculation API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        jurisdictions_available=list(CALCULATORS.keys())
    )


@app.post("/api/v1/calculate/{jurisdiction}", 
          response_model=PayrollCalculationResult,
          tags=["Calculation"])
async def calculate_payroll(jurisdiction: str, employee: EmployeeInput):
    """
    Calculate payroll for a single employee in a specific jurisdiction.
    
    - **jurisdiction**: curacao, st_maarten, aruba, or bonaire
    - **employee**: Employee data and payroll inputs
    
    Returns detailed payroll calculation with line items.
    """
    jurisdiction = jurisdiction.lower()
    
    if jurisdiction not in CALCULATORS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid jurisdiction. Must be one of: {list(CALCULATORS.keys())}"
        )
    
    # Validate jurisdiction matches employee data
    if employee.jurisdiction != jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Jurisdiction mismatch: URL says '{jurisdiction}' but employee data says '{employee.jurisdiction}'"
        )
    
    try:
        calculator = CALCULATORS[jurisdiction]
        result = calculator.calculate(employee)
        return result
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation error: {str(e)}"
        )


@app.post("/api/v1/calculate/batch",
          response_model=BatchCalculationResponse,
          tags=["Calculation"])
async def calculate_payroll_batch(request: BatchCalculationRequest):
    """
    Calculate payroll for multiple employees across jurisdictions.
    
    Processes a batch of employees and returns results with error handling.
    """
    results = []
    errors = []
    success_count = 0
    error_count = 0
    
    for idx, employee in enumerate(request.employees):
        try:
            jurisdiction = employee.jurisdiction.lower()
            
            if jurisdiction not in CALCULATORS:
                errors.append({
                    "employee_id": employee.employee_id,
                    "index": idx,
                    "error": f"Invalid jurisdiction: {jurisdiction}"
                })
                error_count += 1
                continue
            
            if request.validate_only:
                # Just validate, don't calculate
                success_count += 1
                continue
            
            calculator = CALCULATORS[jurisdiction]
            result = calculator.calculate(employee)
            results.append(result)
            success_count += 1
        
        except Exception as e:
            errors.append({
                "employee_id": employee.employee_id,
                "index": idx,
                "error": str(e)
            })
            error_count += 1
    
    return BatchCalculationResponse(
        success_count=success_count,
        error_count=error_count,
        results=results,
        errors=errors
    )


@app.get("/api/v1/jurisdictions", tags=["Info"])
async def list_jurisdictions():
    """List all available jurisdictions and their calculators."""
    return {
        "jurisdictions": [
            {
                "code": "curacao",
                "name": "Curaçao",
                "calculator": "CuracaoCalculator",
                "status": "implemented"
            },
            {
                "code": "st_maarten",
                "name": "St. Maarten",
                "calculator": "StMaartenCalculator",
                "status": "placeholder"
            },
            {
                "code": "aruba",
                "name": "Aruba",
                "calculator": "ArubaCalculator",
                "status": "placeholder"
            },
            {
                "code": "bonaire",
                "name": "Bonaire",
                "calculator": "BonaireCalculator",
                "status": "placeholder"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
