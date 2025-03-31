# tests/core/test_target_company_data.py
import pytest
from dataclasses import is_dataclass

# Imports should work when run via 'poetry run pytest'
from src.core.target_company_data import TargetCompanyData
from src.core.developing_letter import CooperationPoint # Dependency

# --- Fixtures (Optional but good practice) ---
@pytest.fixture
def minimal_target_data():
    """Provides a TargetCompanyData instance with minimal required args."""
    return TargetCompanyData(
        website="http://example.com",
        recipient_email="test@example.com",
        company_name="Example Corp",
        contact_person="Jane Doe",
        process_flag="yes"
    )

@pytest.fixture
def full_target_data():
    """Provides a TargetCompanyData instance with more fields populated."""
    return TargetCompanyData(
        website="http://tech.co",
        recipient_email="john.smith@tech.co",
        company_name=" Tech Solutions Inc. ", # Note leading/trailing spaces
        contact_person="John Smith",
        process_flag=" no ", # Note spaces and case
        main_business="Software Development",
        cooperation_points_str="Point 1; Point 2",
        cooperation_points_list=[CooperationPoint("Point 1"), CooperationPoint("Point 2")],
        generated_letter_subject="Initial Subject",
        generated_letter_body="<p>Initial Body</p>",
        processing_status="Pending",
        draft_id="draft123"
    )

# --- Test Cases ---

def test_target_company_data_creation_minimal(minimal_target_data):
    """Tests creation with minimal arguments and checks defaults."""
    data = minimal_target_data
    assert data.website == "http://example.com"
    assert data.recipient_email == "test@example.com"
    assert data.company_name == "Example Corp"
    assert data.contact_person == "Jane Doe"
    assert data.process_flag == "yes"
    # Check defaults
    assert data.main_business is None
    assert data.cooperation_points_str is None
    assert data.cooperation_points_list == []
    assert data.generated_letter_subject is None
    assert data.generated_letter_body is None
    assert data.processing_status is None
    assert data.draft_id is None
    assert is_dataclass(data)
    # Should not be frozen
    assert getattr(data, '__dataclass_params__').frozen is False

def test_target_company_data_creation_full(full_target_data):
    """Tests creation with all arguments provided."""
    data = full_target_data
    assert data.website == "http://tech.co"
    assert data.recipient_email == "john.smith@tech.co"
    assert data.company_name == " Tech Solutions Inc. " # Keeps spaces as is unless __post_init__ cleans
    assert data.contact_person == "John Smith"
    assert data.process_flag == " no "
    assert data.main_business == "Software Development"
    assert data.cooperation_points_str == "Point 1; Point 2"
    assert data.cooperation_points_list == [CooperationPoint("Point 1"), CooperationPoint("Point 2")]
    assert data.generated_letter_subject == "Initial Subject"
    assert data.generated_letter_body == "<p>Initial Body</p>"
    assert data.processing_status == "Pending"
    assert data.draft_id == "draft123"

@pytest.mark.parametrize("flag_input, expected_result", [
    ("yes", True),
    ("YES", True),
    (" yes ", True),
    (" Yes ", True),
    ("no", False),
    ("NO", False),
    (" no ", False),
    ("nO ", False),
    ("", False),
    ("maybe", False),
    (" true ", False), # Only 'yes' (case-insensitive, stripped) is True
])
def test_should_process_logic(flag_input, expected_result):
    """Tests the should_process property logic."""
    data = TargetCompanyData("w", "e", "c", "p", process_flag=flag_input)
    assert data.should_process == expected_result

def test_update_status(minimal_target_data):
    """Tests the update_status method."""
    data = minimal_target_data
    assert data.processing_status is None
    data.update_status("Success")
    assert data.processing_status == "Success"
    data.update_status("Error: API Failure")
    assert data.processing_status == "Error: API Failure"

def test_set_letter_content(minimal_target_data):
    """Tests the set_letter_content method."""
    data = minimal_target_data
    assert data.generated_letter_subject is None
    assert data.generated_letter_body is None
    subj = "New Subject"
    body = "<p>Test Body</p>"
    data.set_letter_content(subj, body)
    assert data.generated_letter_subject == subj
    assert data.generated_letter_body == body

def test_set_draft_id(minimal_target_data):
    """Tests the set_draft_id method."""
    data = minimal_target_data
    assert data.draft_id is None
    d_id = "xyz789"
    data.set_draft_id(d_id)
    assert data.draft_id == d_id

def test_mutability(minimal_target_data):
    """Tests that attributes can be changed since it's not frozen."""
    data = minimal_target_data
    data.company_name = "New Company Name"
    assert data.company_name == "New Company Name"

    data.main_business = "Updated Business"
    assert data.main_business == "Updated Business"

    data.cooperation_points_list.append(CooperationPoint("Added Later"))
    assert data.cooperation_points_list == [CooperationPoint("Added Later")]

# If you uncomment and implement __post_init__ for cleaning, add tests for it:
# def test_post_init_cleaning():
#     """Tests cleaning logic in __post_init__ (if implemented)."""
#     data = TargetCompanyData(
#         website=" w ", recipient_email=" e ", company_name=" CName ",
#         contact_person=" CP ", process_flag=" yes "
#     )
#     # Assert based on the cleaning rules implemented in __post_init__
#     # Example: assert data.company_name == "CName"
#     pass # Implement test based on actual cleaning