import pytest

from reparsec.scannerless import literal
from reparsec.sequence import eof


def test_many_unconsumed() -> None:
    with pytest.raises(RuntimeError):
        eof().many().parse("")
    with pytest.raises(RuntimeError):
        eof().many().parse("", recover=True)


def test_literal_empty() -> None:
    with pytest.raises(ValueError):
        literal("")
