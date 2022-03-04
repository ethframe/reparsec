import re
from typing import Optional, TypeVar, Union

from .result import (
    Error, Insert, Ok, Recovered, Repair, Result, Selected, Skip
)
from .state import Ctx, Loc
from .types import ParseFn, RecoveryMode

C = TypeVar("C")
V = TypeVar("V")


def get_loc(loc: Loc, stream: str, pos: int) -> Loc:
    start, line, col = loc
    nlc = stream.count("\n", start, pos)
    if nlc:
        line += nlc
        col = pos - stream.rfind("\n", start, pos) - 1
    else:
        col += (pos - start)
    return Loc(pos, line, col)


def literal(s: str) -> ParseFn[str, str]:
    if len(s) == 0:
        raise ValueError("Expected non-empty value")

    ls = len(s)
    rs = repr(s)
    expected = [rs]

    def literal(
            stream: str, pos: int, ctx: Ctx[str],
            rm: RecoveryMode) -> Result[str, str]:
        if stream.startswith(s, pos):
            return Ok(
                s, pos + ls, ctx.update_loc(stream, pos + ls), consumed=True
            )
        loc = ctx.get_loc(stream, pos)
        if rm:
            pending = [Repair(s, pos, ctx, Insert(rs, loc), expected)]
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    skip = cur - pos
                    sel = Selected(
                        cur, s, cur + ls, ctx.update_loc(stream, cur + ls),
                        Skip(skip, loc), expected
                    )
                    return Recovered(sel, pending, pos, loc, expected)
                cur += 1
            return Recovered(None, pending, pos, loc, expected)
        return Error(pos, loc, expected)

    return literal


def regexp(pat: str, group: Union[int, str] = 0) -> ParseFn[str, str]:
    match = re.compile(pat).match
    group = group

    def regexp(
            stream: str, pos: int, ctx: Ctx[str],
            rm: RecoveryMode) -> Result[str, str]:
        r = match(stream, pos=pos)
        if r is not None:
            v: Optional[str] = r.group(group)
            if v is not None:
                end = r.end()
                return Ok(
                    v, end, ctx.update_loc(stream, end), consumed=end != pos
                )
        loc = ctx.get_loc(stream, pos)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        skip = cur - pos
                        end = r.end()
                        sel = Selected(
                            cur, v, end, ctx.update_loc(stream, end),
                            Skip(skip, loc)
                        )
                        return Recovered(sel, [], pos, loc)
                cur += 1
        return Error(pos, loc)

    return regexp
