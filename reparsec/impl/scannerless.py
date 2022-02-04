import re
from typing import AnyStr, Optional, Union

from ..core import ParseFn, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result, Skip


def prefix(s: AnyStr) -> ParseFn[AnyStr, int, AnyStr]:
    ls = len(s)
    rs = repr(s)
    expected = [rs]

    def prefix(
            stream: AnyStr, pos: int, rm: RecoveryMode) -> Result[int, AnyStr]:
        if stream.startswith(s, pos):
            return Ok(s, pos + ls, consumed=ls != 0)
        if rm:
            reps = {pos: Repair(ls, s, Insert(rs, pos), expected)}
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    skip = cur - pos
                    reps[cur + ls] = Repair(skip, s, Skip(skip, pos), expected)
                    return Recovered(reps, pos, expected)
                cur += 1
            return Recovered(reps, pos, expected)
        return Error(pos, expected)

    return prefix


def regexp(
        pat: AnyStr,
        group: Union[int, str] = 0) -> ParseFn[AnyStr, int, AnyStr]:
    match = re.compile(pat).match

    def regexp(
            stream: AnyStr, pos: int, rm: RecoveryMode) -> Result[int, AnyStr]:
        r = match(stream, pos=pos)
        if r is not None:
            v: Optional[AnyStr] = r.group(group)
            if v is not None:
                p = r.end()
                return Ok(v, p, consumed=p != pos)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        skip = cur - pos
                        return Recovered(
                            {r.end(): Repair(skip, v, Skip(skip, pos))}, pos
                        )
                cur += 1
        return Error(pos)

    return regexp
