import re
from typing import Optional, Tuple, TypeVar, Union

from ..core import ParseFn, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result, Skip

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


def eof() -> ParseFn[str, Pos, None]:
    def eof(stream: str, pos: Pos, rm: RecoveryMode) -> Result[Pos, None]:
        start = pos[0]
        if start == len(stream):
            return Ok(None, pos)
        if rm:
            skip = len(stream) - start
            return Recovered(
                {
                    _update_pos(stream, pos, len(stream)): Repair(
                        skip, None, Skip(skip, pos), ["end of file"]
                    )
                },
                pos, ["end of file"]
            )
        return Error(pos, ["end of file"])

    return eof


def prefix(s: str) -> ParseFn[str, Pos, str]:
    ls = len(s)
    rs = repr(s)
    expected = [rs]

    def prefix(stream: str, pos: Pos, rm: RecoveryMode) -> Result[Pos, str]:
        start = pos[0]
        if stream.startswith(s, start):
            return Ok(
                s, _update_pos(stream, pos, start + ls), consumed=ls != 0
            )
        if rm:
            reps = {pos: Repair(ls, s, Insert(rs, pos), expected)}
            cur = start + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    skip = cur - start
                    reps[_update_pos(stream, pos, cur + ls)] = Repair(
                        skip, s, Skip(skip, pos), expected
                    )
                    return Recovered(reps, pos, expected)
                cur += 1
            return Recovered(reps, pos, expected)
        return Error(pos, expected)

    return prefix


def regexp(pat: str, group: Union[int, str] = 0) -> ParseFn[str, Pos, str]:
    match = re.compile(pat).match

    def regexp(
            stream: str, pos: Pos, rm: RecoveryMode) -> Result[Pos, str]:
        start = pos[0]
        r = match(stream, pos=start)
        if r is not None:
            v: Optional[str] = r.group(group)
            if v is not None:
                p = r.end()
                return Ok(v, _update_pos(stream, pos, p), consumed=p != start)
        if rm:
            cur = start + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        skip = cur - start
                        return Recovered(
                            {
                                _update_pos(stream, pos, r.end()): Repair(
                                    skip, v, Skip(skip, pos)
                                )
                            }, pos
                        )
                cur += 1
        return Error(pos)

    return regexp
