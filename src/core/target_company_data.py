# src/core/target_company_data.py
"""
Defines the data structure for holding information about a target company.
"""
from dataclasses import dataclass, field
from typing import Optional, List

# Assuming CooperationPoint is defined in developing_letter.py
# If necessary, adjust import based on final structure if CooperationPoint moves
from .developing_letter import CooperationPoint

@dataclass
class TargetCompanyData:
    """Represents data collected/processed for a single target company."""
    website: str
    recipient_email: str
    company_name: str
    contact_person: str
    process_flag: str # Store the original 'process' value
    target_language: Optional[str] = None

    # Fields populated during processing
    main_business: Optional[str] = None
    cooperation_points_str: Optional[str] = None # Store raw string from API
    cooperation_points_list: List[CooperationPoint] = field(default_factory=list) # If parsed
    generated_letter_subject: Optional[str] = None
    generated_letter_body: Optional[str] = None
    processing_status: Optional[str] = None # e.g., 'Success', 'Skipped', 'Error: ...'
    draft_id: Optional[str] = None

    @property
    def should_process(self) -> bool:
        """Determines if the company should be processed based on the flag."""
        return self.process_flag.strip().lower() == 'yes'

    def update_status(self, status: str):
        self.processing_status = status

    def set_letter_content(self, subject: str, body: str):
        self.generated_letter_subject = subject
        self.generated_letter_body = body

    def set_draft_id(self, draft_id: str):
        self.draft_id = draft_id

    # Optional: Add basic cleaning in post_init if desired
    # def __post_init__(self):
    #     # Example cleaning
    #     self.company_name = self.company_name.strip()
    #     # Add more cleaning as needed