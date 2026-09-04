"""Basic calculator module providing fundamental arithmetic operations."""

from typing import Union

Number = Union[int, float]


def _validate_number(val: Number, param_name: str) -> None:
    """Validate that a given argument is an integer or float."""
    # Note: bool is a subclass of int in Python, so explicitly exclude it
    if not isinstance(val, (int, float)) or isinstance(val, bool):
        raise TypeError(f"Argument '{param_name}' must be an int or float, got {type(val).__name__}")


def add(a: Number, b: Number) -> Number:
    """Add two numbers together.

    Args:
        a (int | float): The first number.
        b (int | float): The second number.

    Returns:
        int | float: The sum of `a` and `b`.

    Raises:
        TypeError: If either `a` or `b` is not an int or float.
    """
    _validate_number(a, "a")
    _validate_number(b, "b")
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """Subtract the second number from the first number.

    Args:
        a (int | float): The number to subtract from.
        b (int | float): The number to subtract.

    Returns:
        int | float: The difference between `a` and `b`.

    Raises:
        TypeError: If either `a` or `b` is not an int or float.
    """
    _validate_number(a, "a")
    _validate_number(b, "b")
    return a - b
