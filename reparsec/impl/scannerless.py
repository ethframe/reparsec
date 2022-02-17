import re
from typing import Optional, Tuple, TypeVar, Union

from ..core import ParseFn, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result, Skip
from ..state import Ctx, Loc

C = TypeVar("C")
V = TypeVar("V")


def _update_loc(stream: str, loc: Loc, end: int) -> Loc:
    start, line, col = loc
    nlc = stream.count("\n", start, end)
    if nlc:
        line += nlc
        col = end - stream.rfind("\n", start, end) - 1
    else:
        col += (end - start)
    return Loc(end, line, col)


class SlCtx(Ctx[str]):
    def get_loc(self, stream: str, pos: int) -> Tuple[Ctx[str], Loc]:
        loc = _update_loc(stream, self.loc, pos)
        return SlCtx(self.anchor, loc), loc

    def set_anchor(self, stream: str, pos: int) -> Tuple[Ctx[str], Ctx[str]]:
        loc = _update_loc(stream, self.loc, pos)
        return SlCtx(self.anchor, loc), SlCtx(loc.col, loc)


def prefix(s: str) -> ParseFn[str, str]:
    if len(s) == 0:
        raise ValueError("Expected non-empty value")

    ls = len(s)
    rs = repr(s)
    expected = [rs]

    def prefix(
            stream: str, pos: int, ctx: Ctx[str],
            rm: RecoveryMode) -> Result[str, str]:
        if stream.startswith(s, pos):
            return Ok(s, pos + ls, ctx, consumed=True)
        ctx, loc = ctx.get_loc(stream, pos)
        if rm:
            reps = {pos: Repair(ls, s, ctx, Insert(rs, loc), expected)}
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    skip = cur - pos
                    reps[cur + ls] = Repair(
                        skip, s, ctx, Skip(skip, loc), expected
                    )
                    return Recovered(reps, pos, loc, expected)
                cur += 1
            return Recovered(reps, pos, loc, expected)
        return Error(pos, loc, expected)

    return prefix


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
                return Ok(v, end, ctx, consumed=end != pos)
        ctx, loc = ctx.get_loc(stream, pos)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        skip = cur - pos
                        return Recovered(
                            {r.end(): Repair(skip, v, ctx, Skip(skip, loc))},
                            pos, loc
                        )
                cur += 1
        return Error(pos, loc)

    return regexp
