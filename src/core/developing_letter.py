# src/core/developing_letter.py
"""
Defines abstractions related to the business developing letter.
"""
from dataclasses import dataclass, field
from typing import List, Protocol, runtime_checkable, Optional, Any
from abc import ABC, abstractmethod

# --- Entities ---
@dataclass(frozen=True)
class CooperationPoint:
    """Represents a single point of potential cooperation."""
    point: str

@dataclass(frozen=True)
class DevelopingLetter:
    """Represents the generated content of a business developing letter."""
    subject: str
    body_html: str

# --- Interfaces ---
# Made LetterGenerationInput a concrete dataclass
@dataclass(frozen=True) # Use frozen=True if input data shouldn't change after creation
class LetterGenerationInput:
    """Defines the structure for data needed to generate a letter."""
    cooperation_points: str
    target_company_name: str
    contact_person_name: str
    # Add other fields if your generator implementation needs them
    # e.g., skyfend_business_info: Optional[str] = None
    #       target_company_business: Optional[str] = None

# Interface for a Letter Generator
class LetterGenerator(ABC):
    """Abstract Base Class defining the interface for any letter generator."""
    @abstractmethod
    def generate(self, input_data: LetterGenerationInput) -> DevelopingLetter:
        """Generates a developing letter."""
        pass