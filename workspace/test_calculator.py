import pytest
from calculator import add, subtract


def test_add_standard_operations():
    """Test addition with standard positive and negative integers."""
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(-5, -5) == -10


def test_subtract_standard_operations():
    """Test subtraction with standard positive and negative integers."""
    assert subtract(10, 5) == 5
    assert subtract(0, 5) == -5
    assert subtract(-3, -3) == 0


def test_add_floating_point_precision():
    """Test addition with floating-point numbers requiring precision handling."""
    assert add(0.1, 0.2) == pytest.approx(0.3)
    assert add(1.0000001, 2.0000002) == pytest.approx(3.0000003)


def test_subtract_floating_point_precision():
    """Test subtraction with floating-point numbers requiring precision handling."""
    assert subtract(0.3, 0.1) == pytest.approx(0.2)
    assert subtract(1.0000003, 1.0000001) == pytest.approx(0.0000002)


def test_add_zero_values():
    """Test addition edge cases involving zero."""
    assert add(0, 0) == 0
    assert add(0, 5) == 5
    assert add(5, 0) == 5


def test_subtract_zero_values():
    """Test subtraction edge cases involving zero."""
    assert subtract(0, 0) == 0
    assert subtract(5, 0) == 5
    assert subtract(0, 5) == -5


def test_add_type_validation():
    """Test that invalid non-numeric inputs raise a TypeError on add."""
    with pytest.raises(TypeError):
        add("5", 3)
    with pytest.raises(TypeError):
        add(5, None)
    with pytest.raises(TypeError):
        add([], 2.5)


def test_subtract_type_validation():
    """Test that invalid non-numeric inputs raise a TypeError on subtract."""
    with pytest.raises(TypeError):
        subtract("10", "5")
    with pytest.raises(TypeError):
        subtract(None, 5)
    with pytest.raises(TypeError):
        subtract(10, {})
