import sys
from pathlib import Path

# Make the workspace folder available for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo_calculator import add, subtract


def test_add():
    assert add(10, 5) == 15


def test_subtract():
    assert subtract(10, 5) == 5


def test_add_negative_numbers():
    assert add(-10, 5) == -5


def test_subtract_negative_numbers():
    assert subtract(-10, 5) == -15


def test_add_zero():
    assert add(10, 0) == 10


def test_subtract_zero():
    assert subtract(10, 0) == 10


def test_add_floats():
    assert add(2.5, 1.5) == 4.0


def test_subtract_floats():
    assert subtract(2.5, 1.5) == 1.0