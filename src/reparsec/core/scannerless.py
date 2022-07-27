import re
from typing import List, Optional, TypeVar, Union

from .parser import ParseFn
from .repair import Repair, make_insert, make_skip
from .result import Error, Ok, Recovered, Result
from .types import Ctx, Loc, RecoveryState

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
    ss = repr(s)
    expected = [ss]

    def literal(
            stream: str, pos: int, ctx: Ctx[str],
            rs: RecoveryState) -> Result[str, str]:
        if stream.startswith(s, pos):
            return Ok(s, pos + ls, ctx.update_loc(stream, pos + ls), (), True)
        loc = ctx.get_loc(stream, pos)
        if rs:
            reps: List[Repair[str, str]] = []
            if rs[0]:
                reps.append(make_insert(rs[0], s, pos, ctx, loc, ss, expected))
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    reps.append(
                        make_skip(
                            rs[0], s, cur + ls,
                            ctx.update_loc(stream, cur + ls), loc, cur - pos,
                            expected
                        )
                    )
                    return Recovered(reps, cur - pos, loc, expected)
                cur += 1
            return Recovered(reps, None, loc, expected)
        return Error(loc, expected)

    return literal


def regexp(pat: str, group: Union[int, str] = 0) -> ParseFn[str, str]:
    match = re.compile(pat).match
    group = group

    def regexp(
            stream: str, pos: int, ctx: Ctx[str],
            rs: RecoveryState) -> Result[str, str]:
        r = match(stream, pos=pos)
        if r is not None:
            v: Optional[str] = r.group(group)
            if v is not None:
                end = r.end()
                return Ok(v, end, ctx.update_loc(stream, end), (), end != pos)
        loc = ctx.get_loc(stream, pos)
        if rs:
            cur = pos + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        end = r.end()
                        return Recovered(
                            [
                                make_skip(
                                    rs[0], v, end, ctx.update_loc(stream, end),
                                    loc, cur - pos
                                )
                            ], cur - pos, loc
                        )
                cur += 1
        return Error(loc)

    return regexp
