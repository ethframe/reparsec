import re
from typing import AnyStr, Optional, Union

from .core import ParseFn, RecoveryMode
from .result import Error, Ok, Recovered, Repair, Result, Skip


def prefix(s: AnyStr) -> ParseFn[AnyStr, AnyStr]:
    expected = [repr(s)]

    def prefix(stream: AnyStr, pos: int, rm: RecoveryMode) -> Result[AnyStr]:
        if stream.startswith(s, pos):
            return Ok(s, pos + len(s), consumed=len(s) != 0)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    skip = cur - pos
                    return Recovered({
                        cur + len(s): Repair(
                            skip, s, Skip(skip, pos), expected
                        )
                    })
                cur += 1
        return Error(pos, expected)

    return prefix


def regexp(pat: AnyStr, group: Union[int, str] = 0) -> ParseFn[AnyStr, AnyStr]:
    match = re.compile(pat).match

    def regexp(stream: AnyStr, pos: int, rm: RecoveryMode) -> Result[AnyStr]:
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
                            {r.end(): Repair(skip, v, Skip(skip, pos))}
                        )
                cur += 1
        return Error(pos)

    return regexp
