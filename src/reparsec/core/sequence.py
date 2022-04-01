from typing import Callable, Optional, Sequence, Sized, TypeVar

from .parser import ParseFn
from .recovery import make_insert, make_skip
from .result import Error, Ok, Recovered, Result
from .types import Ctx, RecoveryMode

T = TypeVar("T")


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
                make_skip(sl, None, sl, ctx, loc, sl - pos, ["end of file"]),
                None, loc, ["end of file"]
            )
        return Error(loc, ["end of file"])

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
                        make_skip(
                            cur, t, cur + 1, ctx.update_loc(stream, cur + 1),
                            loc, cur - pos, consumed=True
                        ),
                        None, loc
                    )
                cur += 1
        return Error(loc)

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
            pending = make_insert(s, pos, ctx, loc, label_, expected)
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    sel = make_skip(
                        cur, t, cur + 1, ctx.update_loc(stream, cur + 1),
                        loc, cur - pos, expected, True
                    )
                    return Recovered(sel, pending, loc, expected)
                cur += 1
            return Recovered(None, pending, loc, expected)
        return Error(loc, expected)

    return sym
