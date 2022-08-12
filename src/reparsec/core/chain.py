from typing import Generic, Iterable, Iterator, TypeVar

A = TypeVar("A")
A_co = TypeVar("A_co", covariant=True)
B = TypeVar("B")


class _Pair(Generic[A, B]):
    __slots__ = "_fst", "_snd"

    def __init__(self, fst: A, snd: B):
        self._fst = fst
        self._snd = snd


class Append(_Pair[Iterable[A_co], Iterable[A_co]], Iterable[A_co]):
    def __iter__(self) -> Iterator[A_co]:
        yield from self._fst
        yield from self._snd

    def __repr__(self) -> str:
        return "<{!r}>".format(list(self))
