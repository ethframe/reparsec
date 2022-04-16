"""
Public API.
"""

from . import layout, lexer, primitive, scannerless, sequence
from .core.result import Insert, RepairOp, Skip
from .core.types import Loc
from .parser import (
    Delay, Parser, Tuple2, Tuple3, Tuple4, Tuple5, Tuple6, Tuple7, Tuple8,
    TupleParser, alt, attempt, between, bind, chainl1, chainr1, fmap,
    insert_on_error, label, many, maybe, sep_by, seq, seql, seqr
)
from .types import ErrorItem, ParseError, ParseResult

__all__ = (
    "layout", "lexer", "primitive", "scannerless", "sequence",
    "Insert", "RepairOp", "Skip",
    "Loc",
    "ErrorItem", "ParseError", "ParseResult",

    "Delay", "Parser", "Tuple2", "Tuple3", "Tuple4", "Tuple5", "Tuple6",
    "Tuple7", "Tuple8", "TupleParser", "alt", "attempt", "between", "bind",
    "chainl1", "chainr1", "fmap", "insert_on_error", "label", "many", "maybe",
    "sep_by", "seq", "seql", "seqr"
)

__version__ = "0.3.5"
