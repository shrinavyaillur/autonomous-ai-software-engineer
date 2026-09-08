"""Simple Task Calculator Module providing basic arithmetic operations."""

from typing import Union

Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """Add two numbers and return the result.

    Args:
        a (Number): First number.
        b (Number): Second number.

    Returns:
        Number: Sum of a and b.
    """
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """Subtract b from a and return the result.

    Args:
        a (Number): First number.
        b (Number): Second number.

    Returns:
        Number: Difference between a and b.
    """
    return a - b


if __name__ == "__main__":
    print("Calculator Test Run:")
    print(f"5 + 3 = {add(5, 3)}")
    print(f"10 - 4 = {subtract(10, 4)}")
