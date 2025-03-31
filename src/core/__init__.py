# src/core/__init__.py
"""Core package: business logic abstractions, entities, interfaces."""

from .my_own_company_business_data import MyOwnCompanyBusinessData
from .target_company_data import TargetCompanyData
from .developing_letter import (
    CooperationPoint,
    DevelopingLetter,
    LetterGenerationInput,
    LetterGenerator
)

__all__ = [
    "MyOwnCompanyBusinessData",
    "TargetCompanyData",
    "CooperationPoint",
    "DevelopingLetter",
    "LetterGenerationInput",
    "LetterGenerator",
]