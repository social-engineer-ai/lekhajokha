from decimal import Decimal

from pydantic import BaseModel


class GSTReturnRequest(BaseModel):
    month: int  # 1-12
    year: int


class GSTR1Response(BaseModel):
    period: str  # "MMYYYY"
    gstin: str
    b2b: list[dict]
    b2cs: list[dict]
    hsn: list[dict]
    total_invoices: int
    total_taxable: float
    total_tax: float


class GSTR3BResponse(BaseModel):
    period: str
    gstin: str
    outward_supplies: dict
    inter_state_supplies: dict
    eligible_itc: dict
    tax_liability: dict
    total_output_tax: float
    total_itc: float
    net_tax_payable: float


class GSTSummary(BaseModel):
    period: str
    total_sales_invoices: int
    total_purchase_invoices: int
    total_output_tax: float
    total_input_tax: float
    net_tax_liability: float
