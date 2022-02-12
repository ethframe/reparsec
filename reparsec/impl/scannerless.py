import re
from typing import Optional, Tuple, TypeVar, Union

from ..core import ParseObjC, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result, Skip

C = TypeVar("C")
V = TypeVar("V")
Pos = Tuple[int, int, int]


def start() -> Pos:
    return (0, 0, 0)


def _update_pos(stream: str, pos: Pos, end: int) -> Pos:
    start, line, col = pos
    nlc = stream.count("\n", start, end)
    if nlc:
        line += nlc
        col = (end - start) - stream.rfind("\n", start, end) - 1
    else:
        col += (end - start)
    return (end, line, col)


class EofC(ParseObjC[str, Pos, C, None]):
    def parse_fn(
            self, stream: str, pos: Pos, ctx: C,
            rm: RecoveryMode) -> Result[Pos, C, None]:
        start = pos[0]
        if start == len(stream):
            return Ok(None, pos, ctx)
        if rm:
            skip = len(stream) - start
            return Recovered(
                {
                    _update_pos(stream, pos, len(stream)): Repair(
                        skip, None, ctx, Skip(skip, pos), ["end of file"]
                    )
                },
                pos, ["end of file"]
            )
        return Error(pos, ["end of file"])


class PrefixC(ParseObjC[str, Pos, C, str]):
    def __init__(self, s: str):
        self._s = s
        self._ls = len(s)
        self._rs = repr(s)
        self._expected = [self._rs]

    def parse_fn(
            self, stream: str, pos: Pos, ctx: C,
            rm: RecoveryMode) -> Result[Pos, C, str]:
        start = pos[0]
        if stream.startswith(self._s, start):
            return Ok(
                self._s, _update_pos(stream, pos, start + self._ls), ctx,
                consumed=self._ls != 0
            )
        if rm:
            reps = {
                pos: Repair(
                    self._ls, self._s, ctx, Insert(self._rs, pos),
                    self._expected
                )
            }
            cur = start + 1
            while cur < len(stream):
                if stream.startswith(self._s, cur):
                    skip = cur - start
                    reps[_update_pos(stream, pos, cur + self._ls)] = Repair(
                        skip, self._s, ctx, Skip(skip, pos), self._expected
                    )
                    return Recovered(reps, pos, self._expected)
                cur += 1
            return Recovered(reps, pos, self._expected)
        return Error(pos, self._expected)


class RegexpC(ParseObjC[str, Pos, C, str]):
    def __init__(self, pat: str, group: Union[int, str] = 0):
        self._match = re.compile(pat).match
        self._group = group

    def parse_fn(
            self, stream: str, pos: Pos, ctx: C,
            rm: RecoveryMode) -> Result[Pos, C, str]:
        start = pos[0]
        r = self._match(stream, pos=start)
        if r is not None:
            v: Optional[str] = r.group(self._group)
            if v is not None:
                p = r.end()
                return Ok(
                    v, _update_pos(stream, pos, p), ctx, consumed=p != start
                )
        if rm:
            cur = start + 1
            while cur < len(stream):
                r = self._match(stream, pos=cur)
                if r is not None:
                    v = r.group(self._group)
                    if v is not None:
                        skip = cur - start
                        return Recovered(
                            {
                                _update_pos(stream, pos, r.end()): Repair(
                                    skip, v, ctx, Skip(skip, pos)
                                )
                            }, pos
                        )
                cur += 1
        return Error(pos)
