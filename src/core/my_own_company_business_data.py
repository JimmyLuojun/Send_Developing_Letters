# src/core/my_own_company_business_data.py
"""
Defines the data structure for holding the sending company's (Skyfend) business information.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class MyOwnCompanyBusinessData:
    """Represents the essential business information for the sending company."""
    description: str

