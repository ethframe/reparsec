import re
from typing import List, Optional, Pattern, TypeVar, Union

from .parser import ParseFastFn, ParseFn, ParseFns
from .repair import Repair, make_insert, make_skip
from .result import Error, Ok, Recovered, Result, SimpleResult
from .types import Ctx, Loc

A = TypeVar("A")


def get_loc(loc: Loc, stream: str, pos: int) -> Loc:
    start, line, col = loc
    nlc = stream.count("\n", start, pos)
    if nlc:
        line += nlc
        col = pos - stream.rfind("\n", start, pos) - 1
    else:
        col += (pos - start)
    return Loc(pos, line, col)


def _literal_fast(s: str) -> ParseFastFn[str, str]:
    ls = len(s)
    expected = [repr(s)]

    def literal(
            stream: str, pos: int, ctx: Ctx[str]) -> SimpleResult[str, str]:
        if stream.startswith(s, pos):
            return Ok(s, pos + ls, ctx.update_loc(stream, pos + ls), (), True)
        return Error(ctx.get_loc(stream, pos), expected)

    return literal


def _literal(s: str) -> ParseFn[str, str]:
    ls = len(s)
    ss = repr(s)
    expected = [ss]

    def literal(
            stream: str, pos: int, ctx: Ctx[str], ins: int,
            rem: Optional[int]) -> Result[str, str]:
        if stream.startswith(s, pos):
            return Ok(s, pos + ls, ctx.update_loc(stream, pos + ls), (), True)
        if rem is None:
            return Error(ctx.get_loc(stream, pos), expected)
        loc = ctx.get_loc(stream, pos)
        reps: List[Repair[str, str]] = []
        if rem:
            reps.append(make_insert(rem, s, pos, ctx, loc, ss, expected))
        cur = pos + 1
        while cur < len(stream):
            if stream.startswith(s, cur):
                reps.append(
                    make_skip(
                        ins, s, cur + ls, ctx.update_loc(stream, cur + ls),
                        loc, cur - pos, expected
                    )
                )
                return Recovered(reps, cur - pos, loc, expected)
            cur += 1
        return Recovered(reps, None, loc, expected)

    return literal


def literal(s: str) -> ParseFns[str, str]:
    if len(s) == 0:
        raise ValueError("Expected non-empty value")

    return ParseFns(_literal_fast(s), _literal(s))


def _regexp_fast(
        pat: Pattern[str], group: Union[int, str]) -> ParseFastFn[str, str]:
    match = pat.match

    def regexp(stream: str, pos: int, ctx: Ctx[str]) -> SimpleResult[str, str]:
        r = match(stream, pos=pos)
        if r is not None:
            v: Optional[str] = r.group(group)
            if v is not None:
                end = r.end()
                return Ok(v, end, ctx.update_loc(stream, end), (), end != pos)
        return Error(ctx.get_loc(stream, pos))

    return regexp


def _regexp(pat: Pattern[str], group: Union[int, str]) -> ParseFn[str, str]:
    match = pat.match

    def regexp(
            stream: str, pos: int, ctx: Ctx[str], ins: int,
            rem: Optional[int]) -> Result[str, str]:
        r = match(stream, pos=pos)
        if r is not None:
            v: Optional[str] = r.group(group)
            if v is not None:
                end = r.end()
                return Ok(v, end, ctx.update_loc(stream, end), (), end != pos)
        if rem is None:
            return Error(ctx.get_loc(stream, pos))
        loc = ctx.get_loc(stream, pos)
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
                                ins, v, end, ctx.update_loc(stream, end), loc,
                                cur - pos
                            )
                        ], cur - pos, loc
                    )
            cur += 1
        return Error(loc)

    return regexp


def regexp(pat: str, group: Union[int, str]) -> ParseFns[str, str]:
    p = re.compile(pat)
    return ParseFns(_regexp_fast(p, group), _regexp(p, group))
