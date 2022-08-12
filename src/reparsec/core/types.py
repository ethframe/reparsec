from typing import Callable, Generic, NamedTuple, TypeVar

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
A = TypeVar("A")
A_co = TypeVar("A_co", covariant=True)


class Loc(NamedTuple):
    pos: int
    line: int
    col: int


class Ctx(Generic[S_contra]):
    __slots__ = "mark", "loc", "_get_loc"

    def __init__(
            self, mark: int, loc: Loc,
            get_loc: Callable[[Loc, S_contra, int], Loc]):
        self.mark = mark
        self.loc = loc
        self._get_loc = get_loc

    def get_loc(self, stream: S_contra, pos: int) -> Loc:
        return self._get_loc(self.loc, stream, pos)

    def update_loc(self, stream: S_contra, pos: int) -> "Ctx[S_contra]":
        if pos == self.loc.pos:
            return self
        return Ctx(
            self.mark, self._get_loc(self.loc, stream, pos), self._get_loc
        )

    def set_mark(self, mark: int) -> "Ctx[S_contra]":
        return Ctx(mark, self.loc, self._get_loc)
