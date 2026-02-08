"""
Curaçao Payroll Calculator - 2026 Official Rates

Implements wage tax (loonbelasting), AOV, AWW, BVZ, AVBZ calculations
according to Curaçao tax laws and SVB regulations for 2026.

Sources:
- SVB 2026 Premium Rates
- Inspectie der Belastingen Handleiding Loonbelasting 2019 (methodology)
- 2026 Toeslagen (Tax Credits)
- 2026 Maandtabel (Monthly Tax Table)
"""
from decimal import Decimal
from typing import Dict, List, Tuple
import csv
import os

from app.models import EmployeeInput
from app.calculators.base import BasePayrollCalculator


class CuracaoCalculator(BasePayrollCalculator):
    """Payroll calculator for Curaçao jurisdiction - 2026 rates."""
    
    # Path to tax table
    TAX_TABLE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'maandtabel_2026.csv')
    
    # ====================
    # 2026 WAGE TAX BRACKETS (MONTHLY) - DEPRECATED, USE TAX TABLE
    # ====================
    # Kept for reference only. Official calculation uses maandtabel_2026.csv
    TAX_BRACKETS = [
        (Decimal("0"), Decimal("2116.67"), Decimal("0.0975")),        # 9.75% up to NAf 25,400/year
        (Decimal("2116.67"), Decimal("2841.67"), Decimal("0.15")),    # 15% up to NAf 34,100/year
        (Decimal("2841.67"), Decimal("3783.33"), Decimal("0.23")),    # 23% up to NAf 45,400/year
        (Decimal("3783.33"), Decimal("5675"), Decimal("0.30")),       # 30% up to NAf 68,100/year
        (Decimal("5675"), Decimal("8041.67"), Decimal("0.375")),      # 37.5% up to NAf 96,500/year
        (Decimal("8041.67"), Decimal("11825"), Decimal("0.465")),     # 46.5% up to NAf 141,900/year
        (Decimal("11825"), Decimal("999999999"), Decimal("0.465")),   # 46.5% above NAf 141,900/year
    ]
    
    # ====================
    # 2026 TAX CREDITS (ANNUAL)
    # ====================
    BASISAFTREK = Decimal("2915")              # Basic deduction
    ALLEENVERDIENER_TOESLA = Decimal("1779")   # Single earner credit
    OUDEREN_TOESLA = Decimal("1342")           # Senior credit (60+)
    OUDEREN_EXTRA = Decimal("673")             # Additional senior credit (transferable)
    
    KINDERTOESLA = {
        1: Decimal("948"),   # Category 1: Child 16-26 studying abroad (eligible programs)
        2: Decimal("475"),   # Category 2: Child up to 26 studying MBO/HBO/University in Curaçao
        3: Decimal("124"),   # Category 3: Child 16-26 in household, other education
        4: Decimal("96"),    # Category 4: Child under 16 in household
    }
    
    # ====================
    # 2026 FIXED DEDUCTION
    # ====================
    VASTE_AFTREK = Decimal("500")  # Annual fixed deduction for work expenses
    
    # ====================
    # 2026 AOV/AWW (OLD AGE & WIDOW/ER PENSION)
    # ====================
    AOV_AWW_EMPLOYEE_RATE = Decimal("0.065")      # 6.5% employee (was 7% in old calculator)
    AOV_AWW_EMPLOYER_RATE = Decimal("0.095")      # 9.5% employer
    AOV_AWW_TOTAL_RATE = Decimal("0.16")          # 16% total
    AOV_AWW_MAX_ANNUAL = Decimal("100000")        # Max annual premium income: NAf 100,000
    AOV_AWW_MAX_MONTHLY = AOV_AWW_MAX_ANNUAL / Decimal("12")
    
    # ====================
    # 2026 AOV/AWW KORTING (PREMIUM CREDIT)
    # ====================
    KORTING_BASE = Decimal("9340")
    KORTING_PERCENTAGE = Decimal("0.338")  # 33.8%
    KORTING_RATE = Decimal("0.065")        # 6.5%
    KORTING_MAX_INCOME = Decimal("27633")  # Korting becomes zero at this income
    
    # ====================
    # 2026 BVZ (BASIC HEALTH INSURANCE)
    # ====================
    BVZ_EMPLOYEE_RATE = Decimal("0.043")          # 4.3% employee
    BVZ_EMPLOYER_RATE = Decimal("0.093")          # 9.3% employer
    BVZ_TOTAL_RATE = Decimal("0.136")             # 13.6% total
    BVZ_MAX_ANNUAL = Decimal("150000")            # Max annual premium income: NAf 150,000
    BVZ_MAX_MONTHLY = BVZ_MAX_ANNUAL / Decimal("12")
    
    # BVZ Exemption and Gliding Scale
    BVZ_VRIJSTELLING_ANNUAL = Decimal("12000")    # Income below this: no BVZ premium
    BVZ_GLIDING_START = Decimal("12000")
    BVZ_GLIDING_END = Decimal("18000")
    
    # BVZ Gliding Scale Discounts
    BVZ_GLIDING_SCALE = [
        (Decimal("12000"), Decimal("13200"), Decimal("0.038")),   # 3.8% discount
        (Decimal("13200"), Decimal("14400"), Decimal("0.028")),   # 2.8% discount
        (Decimal("14400"), Decimal("15600"), Decimal("0.019")),   # 1.9% discount
        (Decimal("15600"), Decimal("16800"), Decimal("0.011")),   # 1.1% discount
        (Decimal("16800"), Decimal("18000"), Decimal("0.006")),   # 0.6% discount
    ]
    
    # ====================
    # 2026 AVBZ (SPECIAL MEDICAL COSTS)
    # ====================
    AVBZ_EMPLOYEE_RATE = Decimal("0.015")         # 1.5% employee
    AVBZ_EMPLOYER_RATE = Decimal("0.005")         # 0.5% employer
    AVBZ_TOTAL_RATE = Decimal("0.02")             # 2% total
    AVBZ_MAX_ANNUAL = Decimal("606247.08")        # Max annual premium income
    AVBZ_MAX_MONTHLY = AVBZ_MAX_ANNUAL / Decimal("12")
    
    # AVBZ Reduced Rate for Low Income
    AVBZ_REDUCED_THRESHOLD = Decimal("22789")     # Below this: 1% total instead of 2%
    AVBZ_REDUCED_EMPLOYEE = Decimal("0.005")      # 0.5% employee (reduced)
    AVBZ_REDUCED_EMPLOYER = Decimal("0.005")      # 0.5% employer (reduced)
    
    # ====================
    # 2026 CESANTIA (UNEMPLOYMENT)
    # ====================
    # NOTE: Cesantia is EMPLOYER-PAID ONLY (not deducted from employee wages)
    CESANTIA_ANNUAL = Decimal("40")               # Flat XCG 40 per worker per year
    CESANTIA_MONTHLY = CESANTIA_ANNUAL / Decimal("12")
    
    # ====================
    # OTHER SETTINGS
    # ====================
    OVERTIME_MULTIPLIER = Decimal("1.5")
    
    # Tax table cache
    _tax_table_cache = None
    
    @classmethod
    def load_tax_table(cls) -> List[Tuple[Decimal, Decimal, Decimal]]:
        """
        Load the official 2026 monthly tax table (maandtabel).
        Returns list of (min_income, max_income, gross_tax) tuples.
        
        The tax table provides GROSS tax amounts which must be reduced
        by the basisaftrek (NAf 242.92/month) to get final tax.
        """
        if cls._tax_table_cache is not None:
            return cls._tax_table_cache
        
        tax_table = []
        
        # Check if tax table file exists
        if not os.path.exists(cls.TAX_TABLE_PATH):
            # Fallback to progressive brackets if table not available
            return None
        
        try:
            with open(cls.TAX_TABLE_PATH, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if row and row[0] and row[1] and row[2]:
                        min_val = Decimal(row[0])
                        max_val = Decimal(row[1]) if row[1] else Decimal("999999")
                        tax = Decimal(row[2])
                        tax_table.append((min_val, max_val, tax))
        except Exception as e:
            # If table loading fails, return None to use progressive brackets
            return None
        
        cls._tax_table_cache = tax_table
        return tax_table
    
    @classmethod
    def lookup_tax_from_table(cls, tax_base: Decimal) -> Decimal:
        """
        Lookup gross tax from the official monthly tax table.
        
        Args:
            tax_base: Monthly taxable income
            
        Returns:
            Gross tax amount (before basisaftrek deduction)
        """
        tax_table = cls.load_tax_table()
        
        if tax_table is None:
            # Fallback to progressive brackets
            return None
        
        for min_val, max_val, tax in tax_table:
            if min_val <= tax_base < max_val:
                return tax
        
        # If beyond table range, use last entry
        if tax_table:
            return tax_table[-1][2]
        
        return Decimal("0")
    
    
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
    

    def calculate_premium_income_monthly(self, gross: Decimal) -> Decimal:
        """
        Calculate monthly premium income (grondslag) for AOV/AWW/BVZ/AVBZ.
        Premium income = Gross - (Vaste Aftrek / 12)
        """
        monthly_vaste_aftrek = self.VASTE_AFTREK / Decimal("12")
        premium_income = gross - monthly_vaste_aftrek
        return max(premium_income, Decimal("0"))  # Cannot be negative
    
    def calculate_aov_aww_korting_monthly(self, annual_premium_income: Decimal) -> Decimal:
        """
        Calculate the AOV/AWW premium credit (korting) on monthly basis.
        Formula: (NAf 9,340 - (33.8% × premium income)) × 6.5%
        Korting becomes zero when income >= NAf 27,633
        """
        if annual_premium_income >= self.KORTING_MAX_INCOME:
            return Decimal("0")
        
        korting_annual = (self.KORTING_BASE - (self.KORTING_PERCENTAGE * annual_premium_income)) * self.KORTING_RATE
        korting_annual = max(korting_annual, Decimal("0"))  # Cannot be negative
        
        # Convert to monthly
        return korting_annual / Decimal("12")
    
    def calculate_bvz_gliding_discount(self, annual_income: Decimal) -> Decimal:
        """
        Calculate BVZ gliding scale discount for low to middle income.
        Returns discount percentage (e.g., 0.038 for 3.8% discount)
        """
        if annual_income < self.BVZ_GLIDING_START:
            return Decimal("0")  # Below threshold: full exemption handled separately
        
        if annual_income >= self.BVZ_GLIDING_END:
            return Decimal("0")  # Above gliding scale: no discount
        
        # Find applicable discount bracket
        for bracket_start, bracket_end, discount in self.BVZ_GLIDING_SCALE:
            if bracket_start <= annual_income < bracket_end:
                return discount
        
        return Decimal("0")
    
    def calculate_tax(self, employee: EmployeeInput, gross: Decimal) -> Decimal:
        """
        Calculate Curaçao wage tax (loonbelasting) using 2026 OFFICIAL TAX TABLE.
        Uses maandtabel (monthly table) for accurate tax calculation.
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
        
        # STEP 1: Calculate premium income (gross - vaste aftrek/12)
        premium_income_monthly = self.calculate_premium_income_monthly(gross)
        
        # STEP 2: Calculate AOV/AWW deduction first (needed for tax base)
        aov_aww_base = min(premium_income_monthly, self.AOV_AWW_MAX_MONTHLY)
        aov_aww_employee_raw = aov_aww_base * self.AOV_AWW_EMPLOYEE_RATE
        
        # Calculate korting
        premium_income_annual = premium_income_monthly * Decimal("12")
        korting_monthly = Decimal("0")
        if premium_income_annual < self.KORTING_MAX_INCOME:
            korting_monthly = self.calculate_aov_aww_korting_monthly(premium_income_annual)
        
        aov_aww_final = max(aov_aww_employee_raw - korting_monthly, Decimal("0"))
        
        # STEP 3: Calculate tax base = premium income - AOV/AWW final
        tax_base = premium_income_monthly - aov_aww_final
        
        # STEP 4: Try to lookup tax from OFFICIAL TAX TABLE (maandtabel)
        raw_tax = self.lookup_tax_from_table(tax_base)
        
        # If tax table not available, use progressive brackets as fallback
        if raw_tax is None:
            raw_tax, tax_notes = self.calculate_progressive_tax(tax_base, self.TAX_BRACKETS)
            tax_method = "Progressive brackets (fallback)"
        else:
            tax_method = f"Official table lookup (NAf {tax_base:.2f})"
        
        # STEP 5: Apply tax credits (toeslagen) - monthly amounts
        monthly_basisaftrek = self.BASISAFTREK / Decimal("12")
        tax_credits = monthly_basisaftrek
        
        # TODO: Add other tax credits based on employee data:
        # - Alleenverdiener (single earner)
        # - Kindertoesla (child credits)
        # - Ouderentoeslag (senior 60+)
        
        # STEP 6: Final tax = raw tax - credits (but cannot go below 0)
        final_tax = max(raw_tax - tax_credits, Decimal("0"))
        
        self.add_line_item(
            code="TAX",
            name="Wage Tax (Loonbelasting)",
            category="DEDUCTION",
            amount=final_tax,
            base_amount=tax_base,
            notes=f"{tax_method} | Gross tax: NAf {raw_tax:.2f} - Basisaftrek: NAf {tax_credits:.2f}"
        )
        
        return final_tax
    
    def lookup_tax_from_table(self, tax_base: Decimal) -> Decimal:
        """
        Lookup tax from official 2026 monthly tax table (maandtabel).
        Reads from the actual CSV file.
        """
        # Load tax table from CSV
        tax_table_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'maandtabel_2026.csv')
        
        if not os.path.exists(tax_table_path):
            # Fallback to None if file doesn't exist
            return None
        
        try:
            with open(tax_table_path, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if row and len(row) >= 3 and row[0] and row[1] and row[2]:
                        min_val = Decimal(row[0])
                        max_val = Decimal(row[1]) if row[1] else Decimal("999999")
                        tax = Decimal(row[2])
                        
                        # Check if tax_base falls in this range
                        if min_val <= tax_base < max_val:
                            return tax
                
                # If we reach here, tax_base is beyond the table
                # Return the last entry's tax value
                return tax  # Last value from loop
        except Exception as e:
            # If any error, return None to fall back to progressive brackets
            return None
    

    def calculate_social_security(self, employee: EmployeeInput, gross: Decimal) -> Dict[str, Decimal]:
        """
        Calculate Curaçao social security contributions for 2026:
        - AOV/AWW (with premium credit/korting for low income)
        - BVZ (with exemption and gliding scale)
        - AVBZ (with reduced rate for low income)
        - Cesantia (flat annual amount)
        """
        contributions = {}
        
        # Calculate premium income (base for all premiums)
        premium_income_monthly = self.calculate_premium_income_monthly(gross)
        premium_income_annual = premium_income_monthly * Decimal("12")
        
        # ======================
        # AOV/AWW (Combined) - FIRST (matching loonstaat order)
        # ======================
        if not employee.aov_exempt:
            # Cap at maximum
            aov_aww_base = min(premium_income_monthly, self.AOV_AWW_MAX_MONTHLY)
            
            # Calculate employee premium (6.5%)
            aov_aww_employee_raw = aov_aww_base * self.AOV_AWW_EMPLOYEE_RATE
            
            # Add the raw AOV/AWW as a line item
            self.add_line_item(
                code="AOV_AWW",
                name="AOV/AWW (6.5%)",
                category="DEDUCTION",
                amount=aov_aww_employee_raw,
                rate=self.AOV_AWW_EMPLOYEE_RATE,
                base_amount=aov_aww_base,
                notes=f"Pension & Widow/er Insurance"
            )
            
            # Calculate korting (premium credit)
            korting_monthly = Decimal("0")
            if premium_income_annual < self.KORTING_MAX_INCOME:
                korting_monthly = self.calculate_aov_aww_korting_monthly(premium_income_annual)
                korting_note = f"Credit: income < NAf {self.KORTING_MAX_INCOME:,.0f}"
            else:
                korting_note = f"Income >= NAf {self.KORTING_MAX_INCOME:,.0f}"
            
            # Add korting as a NEGATIVE deduction (credit) - shown right after AOV/AWW
            self.add_line_item(
                code="KORTING",
                name="Premie Korting",
                category="DEDUCTION",
                amount=-korting_monthly,  # Negative = reduces deductions
                notes=korting_note
            )
            
            # Final employee premium = raw premium - korting
            aov_aww_employee_final = max(aov_aww_employee_raw - korting_monthly, Decimal("0"))
            contributions['AOV_AWW'] = aov_aww_employee_final
            
        else:
            self.warnings.append("Employee is AOV/AWW exempt")
            contributions['AOV_AWW'] = Decimal("0")
        
        # ======================
        # BVZ (Basic Health Insurance) - SECOND
        # ======================
        # Check exemption threshold
        if premium_income_annual < self.BVZ_VRIJSTELLING_ANNUAL:
            # Full exemption for income below NAf 12,000/year
            self.add_line_item(
                code="BVZ",
                name="BVZ (Health Insurance)",
                category="DEDUCTION",
                amount=Decimal("0"),
                notes=f"Exempt: income below NAf {self.BVZ_VRIJSTELLING_ANNUAL:.2f}/year"
            )
            contributions['BVZ'] = Decimal("0")
            
        else:
            # Cap at maximum
            bvz_base = min(premium_income_monthly, self.BVZ_MAX_MONTHLY)
            
            # Calculate raw premium (4.3%)
            bvz_raw = bvz_base * self.BVZ_EMPLOYEE_RATE
            
            # Apply gliding scale discount if applicable
            gliding_discount = self.calculate_bvz_gliding_discount(premium_income_annual)
            discount_amount = bvz_raw * gliding_discount
            bvz_final = bvz_raw - discount_amount
            
            notes = f"Health Insurance"
            if discount_amount > Decimal("0"):
                notes += f" | Discount: -{gliding_discount * 100:.1f}%"
            
            self.add_line_item(
                code="BVZ",
                name="BVZ (4.3%)",
                category="DEDUCTION",
                amount=bvz_final,
                rate=self.BVZ_EMPLOYEE_RATE,
                base_amount=bvz_base,
                notes=notes
            )
            contributions['BVZ'] = bvz_final
        
        # ======================
        # AVBZ (Special Medical Costs) - THIRD
        # ======================
        # Cap at maximum
        avbz_base = min(premium_income_monthly, self.AVBZ_MAX_MONTHLY)
        
        # Check if reduced rate applies (income < NAf 22,789/year)
        if premium_income_annual < self.AVBZ_REDUCED_THRESHOLD:
            avbz_rate = self.AVBZ_REDUCED_EMPLOYEE  # 0.5%
            rate_note = "0.5% (reduced rate)"
        else:
            avbz_rate = self.AVBZ_EMPLOYEE_RATE  # 1.5%
            rate_note = "1.5%"
        
        avbz_amount = avbz_base * avbz_rate
        
        self.add_line_item(
            code="AVBZ",
            name="AVBZ (Special Medical)",
            category="DEDUCTION",
            amount=avbz_amount,
            rate=avbz_rate,
            base_amount=avbz_base,
            notes=f"{rate_note}"
        )
        contributions['AVBZ'] = avbz_amount
        
        # ======================
        # CESANTIA (Unemployment)
        # ======================
        # NOTE: Cesantia is EMPLOYER-PAID ONLY, not deducted from employee
        # Flat annual amount of XCG 40 = NAf 40
        # This is NOT added as a deduction for the employee
        # It's only shown in employer contributions
        
        contributions['CESANTIA'] = Decimal("0")  # Employee pays nothing
        
        return contributions


# Create singleton instance
curacao_calculator = CuracaoCalculator()
