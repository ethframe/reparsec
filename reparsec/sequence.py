from typing import Callable, Sequence, TypeVar

from .core import ParseFn, ParseObj, RecoveryMode
from .result import Error, Insert, Ok, Recovered, Repair, Result, Skip

T = TypeVar("T", bound=object)


class Eof(ParseObj[Sequence[T], None]):
    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[None]:
        if pos == len(stream):
            return Ok(None, pos)
        if rm:
            skip = len(stream) - pos
            return Recovered([Repair(
                skip, None, len(stream), Skip(skip, pos), ["end of file"]
            )])
        return Error(pos, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> ParseFn[Sequence[T], T]:
    def satisfy(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, consumed=True)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if test(t):
                    skip = cur - pos
                    return Recovered(
                        [Repair(skip, t, cur + 1, Skip(skip, pos))]
                    )
                cur += 1
        return Error(pos)

    return satisfy


def sym(s: T) -> ParseFn[Sequence[T], T]:
    rs = repr(s)
    expected = [rs]

    def sym(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, consumed=True)
        if rm:
            ins = Repair(1, s, pos, Insert(rs, pos), expected)
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    skip = cur - pos
                    return Recovered([
                        ins,
                        Repair(skip, t, cur + 1, Skip(skip, pos), expected)
                    ])
                cur += 1
            return Recovered([ins])
        return Error(pos, expected)

    return sym
