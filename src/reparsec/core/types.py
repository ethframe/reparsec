from typing import Callable, Generic, NamedTuple, Optional, TypeVar

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


class Loc(NamedTuple):
    pos: int
    line: int
    col: int


class Ctx(Generic[S_contra]):
    __slots__ = "anchor", "loc", "max_insertions", "_get_loc"

    def __init__(
            self, anchor: int, loc: Loc, max_insertions: int,
            get_loc: Callable[[Loc, S_contra, int], Loc]):
        self.anchor = anchor
        self.loc = loc
        self.max_insertions = max_insertions
        self._get_loc = get_loc

    def get_loc(self, stream: S_contra, pos: int) -> Loc:
        return self._get_loc(self.loc, stream, pos)

    def update_loc(self, stream: S_contra, pos: int) -> "Ctx[S_contra]":
        if pos == self.loc.pos:
            return self
        return Ctx(
            self.anchor, self._get_loc(self.loc, stream, pos),
            self.max_insertions, self._get_loc
        )

    def set_anchor(self, anchor: int) -> "Ctx[S_contra]":
        return Ctx(anchor, self.loc, self.max_insertions, self._get_loc)

    def decrease_max_insertions(self, count: int) -> "Ctx[S_contra]":
        if self.max_insertions == 0:
            return self
        return Ctx(
            self.anchor, self.loc, max(self.max_insertions - count, 0),
            self._get_loc
        )


RecoveryMode = Optional[bool]


def disallow_recovery(rm: RecoveryMode) -> RecoveryMode:
    if rm is None:
        return None
    return False


def maybe_allow_recovery(
        ctx: Ctx[S], rm: RecoveryMode, consumed: bool) -> RecoveryMode:
    if rm is not None and consumed:
        return bool(ctx.max_insertions)
    return rm
