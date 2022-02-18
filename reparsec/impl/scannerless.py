import re
from typing import Optional, TypeVar, Union

from ..core import ParseFn, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result, Skip
from ..state import Ctx, Loc

C = TypeVar("C")
V = TypeVar("V")


class SlCtx(Ctx[str]):
    def update_loc(self, stream: str, pos: int) -> Ctx[str]:
        start, line, col = self.loc
        if pos == start:
            return self
        nlc = stream.count("\n", start, pos)
        if nlc:
            line += nlc
            col = pos - stream.rfind("\n", start, pos) - 1
        else:
            col += (pos - start)
        return SlCtx(self.anchor, Loc(pos, line, col))

    def set_anchor(self, anchor: int) -> Ctx[str]:
        return SlCtx(anchor, self.loc)


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
            return Ok(
                s, pos + ls, ctx.update_loc(stream, pos + ls), consumed=True
            )
        ctx = ctx.update_loc(stream, pos)
        if rm:
            reps = {pos: Repair(ls, s, ctx, Insert(rs, ctx.loc), expected)}
            cur = pos + 1
            while cur < len(stream):
                if stream.startswith(s, cur):
                    skip = cur - pos
                    reps[cur + ls] = Repair(
                        skip, s, ctx.update_loc(stream, cur + ls),
                        Skip(skip, ctx.loc), expected
                    )
                    return Recovered(reps, pos, ctx.loc, expected)
                cur += 1
            return Recovered(reps, pos, ctx.loc, expected)
        return Error(pos, ctx.loc, expected)

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
                return Ok(
                    v, end, ctx.update_loc(stream, end), consumed=end != pos
                )
        ctx = ctx.update_loc(stream, pos)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                r = match(stream, pos=cur)
                if r is not None:
                    v = r.group(group)
                    if v is not None:
                        skip = cur - pos
                        end = r.end()
                        return Recovered(
                            {
                                end: Repair(
                                    skip, v, ctx.update_loc(stream, end),
                                    Skip(skip, ctx.loc)
                                )
                            },
                            pos, ctx.loc
                        )
                cur += 1
        return Error(pos, ctx.loc)

    return regexp
