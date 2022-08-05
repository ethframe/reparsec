from typing import Callable, Generic, NamedTuple, Tuple, TypeVar, Union

from typing_extensions import Literal

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


class Loc(NamedTuple):
    pos: int
    line: int
    col: int


class Ctx(Generic[S_contra]):
    __slots__ = "mark", "loc", "ins", "_get_loc"

    def __init__(
            self, mark: int, loc: Loc, ins: int,
            get_loc: Callable[[Loc, S_contra, int], Loc]):
        self.mark = mark
        self.loc = loc
        self.ins = ins
        self._get_loc = get_loc

    def get_loc(self, stream: S_contra, pos: int) -> Loc:
        return self._get_loc(self.loc, stream, pos)

    def update_loc(self, stream: S_contra, pos: int) -> "Ctx[S_contra]":
        if pos == self.loc.pos:
            return self
        return Ctx(
            self.mark, self._get_loc(self.loc, stream, pos), self.ins,
            self._get_loc
        )

    def set_anchor(self, mark: int) -> "Ctx[S_contra]":
        return Ctx(mark, self.loc, self.ins, self._get_loc)


RecoveryState = Union[Literal[None, False], Tuple[int]]


def disallow_recovery(ins: RecoveryState) -> RecoveryState:
    if ins is None:
        return None
    return False


def maybe_allow_recovery(
        ctx: Ctx[S], ins: RecoveryState, consumed: bool) -> RecoveryState:
    if ins is False and consumed:
        return (ctx.ins,)
    return ins
