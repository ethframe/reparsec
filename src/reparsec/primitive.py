from typing import TypeVar

from .core import primitive
from .parser import Parser

__all__ = ("Pure", "PureFn", "InsertValue", "InsertFn")

S_contra = TypeVar("S_contra", contravariant=True)
V_co = TypeVar("V_co", covariant=True)


class Pure(primitive.Pure[S_contra, V_co], Parser[S_contra, V_co]):
    pass


class PureFn(primitive.PureFn[S_contra, V_co], Parser[S_contra, V_co]):
    pass


class InsertValue(
        primitive.InsertValue[S_contra, V_co], Parser[S_contra, V_co]):
    pass


class InsertFn(primitive.InsertFn[S_contra, V_co], Parser[S_contra, V_co]):
    pass
