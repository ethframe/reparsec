from typing import Callable, Optional, Sequence, Sized, TypeVar

from .result import (
    Error, Insert, Ok, Pending, Recovered, Result, Selected, Skip
)
from .state import Ctx
from .types import ParseFn, RecoveryMode

T = TypeVar("T")
C = TypeVar("C", bound=object)


def eof() -> ParseFn[Sized, None]:
    def eof(
            stream: Sized, pos: int, ctx: Ctx[Sized],
            rm: RecoveryMode) -> Result[None, Sized]:
        if pos == len(stream):
            return Ok(None, pos, ctx)
        loc = ctx.get_loc(stream, pos)
        if rm:
            sl = len(stream)
            return Recovered(
                Selected(
                    sl, 0, 0, sl, None, ctx, Skip(sl - pos, loc),
                    ["end of file"]
                ),
                None, pos, loc, ["end of file"]
            )
        return Error(pos, loc, ["end of file"])

    return eof


def satisfy(test: Callable[[T], bool]) -> ParseFn[Sequence[T], T]:
    def satisfy(
            stream: Sequence[T], pos: int, ctx: Ctx[Sequence[T]],
            rm: RecoveryMode) -> Result[T, Sequence[T]]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, ctx, consumed=True)
        loc = ctx.get_loc(stream, pos)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if test(t):
                    return Recovered(
                        Selected(
                            cur, 0, 0, cur + 1, t,
                            ctx.update_loc(stream, cur + 1),
                            Skip(cur - pos, loc)
                        ),
                        None, pos, loc
                    )
                cur += 1
        return Error(pos, loc)

    return satisfy


def sym(s: T, label: Optional[str] = None) -> ParseFn[Sequence[T], T]:
    if label is None:
        label_ = repr(s)
    else:
        label_ = label
    expected = [label_]

    def sym(
            stream: Sequence[T], pos: int, ctx: Ctx[Sequence[T]],
            rm: RecoveryMode) -> Result[T, Sequence[T]]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, ctx, consumed=True)
        loc = ctx.get_loc(stream, pos)
        if rm:
            pending = Pending(1, s, ctx, Insert(label_, loc), expected)
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    sel = Selected(
                        cur, 0, 0, cur + 1, t, ctx.update_loc(stream, cur + 1),
                        Skip(cur - pos, loc), expected
                    )
                    return Recovered(sel, pending, pos, loc, expected)
                cur += 1
            return Recovered(None, pending, pos, loc, expected)
        return Error(pos, loc, expected)

    return sym
