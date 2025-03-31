# tests/core/test_my_own_company_business_data.py
import pytest
from dataclasses import is_dataclass, FrozenInstanceError

# Import should work when run via 'poetry run pytest'
from src.core.my_own_company_business_data import MyOwnCompanyBusinessData

def test_my_own_company_business_data_creation():
    """Tests if MyOwnCompanyBusinessData instances are created correctly."""
    description_text = "Skyfend is a leading provider of anti-drone solutions."
    data = MyOwnCompanyBusinessData(description=description_text)

    assert data.description == description_text
    assert is_dataclass(data)
    assert getattr(data, '__dataclass_params__').frozen is True

def test_my_own_company_business_data_is_frozen():
    """Tests that MyOwnCompanyBusinessData instances are immutable."""
    data = MyOwnCompanyBusinessData(description="Initial Description")
    with pytest.raises(FrozenInstanceError):
        data.description = "Trying to change description"