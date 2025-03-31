# tests/core/test_developing_letter.py
import pytest
from dataclasses import is_dataclass, FrozenInstanceError
import abc # Import abc directly for checking

# Poetry handles the path, so this import should work when run via 'poetry run pytest'
from src.core.developing_letter import (
    CooperationPoint,
    DevelopingLetter,
    LetterGenerationInput, # Class exists but has no methods/logic to test directly
    LetterGenerator      # ABC, cannot instantiate directly for testing here
)

# --- Test CooperationPoint ---

def test_cooperation_point_creation():
    """Tests if CooperationPoint instances are created correctly."""
    point_text = "Discuss joint marketing opportunities."
    cp = CooperationPoint(point=point_text)
    assert cp.point == point_text
    assert is_dataclass(cp)
    assert getattr(cp, '__dataclass_params__').frozen is True

def test_cooperation_point_is_frozen():
    """Tests that CooperationPoint instances are immutable."""
    cp = CooperationPoint(point="Initial Point")
    with pytest.raises(FrozenInstanceError):
        cp.point = "Trying to change point"

# --- Test DevelopingLetter ---

def test_developing_letter_creation():
    """Tests if DevelopingLetter instances are created correctly."""
    subject_text = "Potential Partnership Discussion"
    body_html_content = "<p>Dear Partner,</p><p>Let's connect.</p>"
    letter = DevelopingLetter(subject=subject_text, body_html=body_html_content)

    assert letter.subject == subject_text
    assert letter.body_html == body_html_content
    assert is_dataclass(letter)
    assert getattr(letter, '__dataclass_params__').frozen is True

def test_developing_letter_is_frozen():
    """Tests that DevelopingLetter instances are immutable."""
    letter = DevelopingLetter(subject="Initial Subject", body_html="<p>Initial Body</p>")
    with pytest.raises(FrozenInstanceError):
        letter.subject = "Trying to change subject"
    with pytest.raises(FrozenInstanceError):
        letter.body_html = "<p>Trying to change body</p>"

# --- Test LetterGenerationInput (Structure Check) ---
def test_letter_generation_input_structure():
    """Checks the basic structure/attributes of LetterGenerationInput."""
    # No direct instantiation/logic to test from the provided definition
    pass

# --- Test LetterGenerator (Concept Check) ---
def test_letter_generator_is_abc():
    """Checks that LetterGenerator is an Abstract Base Class."""
    assert issubclass(LetterGenerator, abc.ABC)
    assert hasattr(LetterGenerator.generate, '__isabstractmethod__')
    assert LetterGenerator.generate.__isabstractmethod__ is True