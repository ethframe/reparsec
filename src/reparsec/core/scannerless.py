import re
from typing import Optional, TypeVar, Union

from .parser import ParseFn
from .repair import make_insert, make_skip
from .result import Error, Ok, Recovered, Result
from .types import Ctx, Loc, RecoveryMode

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
            return Ok(s, pos + ls, ctx.update_loc(stream, pos + ls), (), True)
        loc = ctx.get_loc(stream, pos)
        if rm:
            pending = (
                make_insert(s, pos, ctx, loc, rs, expected) if rm[0] else None
            )
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    sel = make_skip(
                        cur, s, cur + ls, ctx.update_loc(stream, cur + ls),
                        loc, cur - pos, expected
                    )
                    return Recovered(sel, pending, loc, expected)
                cur += 1
            return Recovered(None, pending, loc, expected)
        return Error(loc, expected)

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
                return Ok(v, end, ctx.update_loc(stream, end), (), end != pos)
        loc = ctx.get_loc(stream, pos)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        end = r.end()
                        sel = make_skip(
                            cur, v, end, ctx.update_loc(stream, end), loc,
                            cur - pos
                        )
                        return Recovered(sel, None, loc)
                cur += 1
        return Error(loc)

    return regexp
