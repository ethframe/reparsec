from typing import Callable, Sequence, Sized, TypeVar

from ..core import ParseObjC, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result, Skip

T = TypeVar("T")
C = TypeVar("C", bound=object)


class EofC(ParseObjC[Sized, int, C, None]):
    def parse_fn(
            self, stream: Sized, pos: int, ctx: C,
            rm: RecoveryMode) -> Result[int, C, None]:
        if pos == len(stream):
            return Ok(None, pos, ctx)
        if rm:
            skip = len(stream) - pos
            return Recovered(
                {
                    len(stream): Repair(
                        skip, None, ctx, Skip(skip, pos), ["end of file"]
                    )
                },
                pos, ["end of file"]
            )
        return Error(pos, ["end of file"])


class SatisfyC(ParseObjC[Sequence[T], int, C, T]):
    def __init__(self, test: Callable[[T], bool]):
        self._test = test

    def parse_fn(
            self, stream: Sequence[T], pos: int, ctx: C,
            rm: RecoveryMode) -> Result[int, C, T]:
        if pos < len(stream):
            t = stream[pos]
            if self._test(t):
                return Ok(t, pos + 1, ctx, consumed=True)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if self._test(t):
                    skip = cur - pos
                    return Recovered(
                        {cur + 1: Repair(skip, t, ctx, Skip(skip, pos))}, pos
                    )
                cur += 1
        return Error(pos)


class SymC(ParseObjC[Sequence[T], int, C, T]):
    def __init__(self, s: T):
        self._s = s
        self._rs = repr(s)
        self._expected = [self._rs]

    def parse_fn(
            self, stream: Sequence[T], pos: int, ctx: C,
            rm: RecoveryMode) -> Result[int, C, T]:
        if pos < len(stream):
            t = stream[pos]
            if t == self._s:
                return Ok(t, pos + 1, ctx, consumed=True)
        if rm:
            reps = {
                pos: Repair(
                    1, self._s, ctx, Insert(self._rs, pos), self._expected
                )
            }
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == self._s:
                    skip = cur - pos
                    reps[cur + 1] = Repair(
                        skip, t, ctx, Skip(skip, pos), self._expected
                    )
                    return Recovered(reps, pos, self._expected)
                cur += 1
            return Recovered(reps, pos, self._expected)
        return Error(pos, self._expected)
