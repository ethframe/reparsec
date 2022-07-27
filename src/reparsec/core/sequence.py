from typing import Callable, List, Optional, Sequence, Sized, TypeVar

from .parser import ParseFn
from .repair import Repair, make_insert, make_pending_skip, make_skip
from .result import Error, Ok, Recovered, Result
from .types import Ctx, RecoveryState

T = TypeVar("T")


def eof() -> ParseFn[Sized, None]:
    def eof(
            stream: Sized, pos: int, ctx: Ctx[Sized],
            rs: RecoveryState) -> Result[None, Sized]:
        if pos == len(stream):
            return Ok(None, pos, ctx)
        loc = ctx.get_loc(stream, pos)
        if rs:
            sl = len(stream)
            return Recovered(
                [
                    make_pending_skip(
                        rs[0], None, sl, ctx, loc, sl - pos, ["end of file"]
                    ),
                ], None, loc, ["end of file"]
            )
        return Error(loc, ["end of file"])

    return eof


def satisfy(test: Callable[[T], bool]) -> ParseFn[Sequence[T], T]:
    def satisfy(
            stream: Sequence[T], pos: int, ctx: Ctx[Sequence[T]],
            rs: RecoveryState) -> Result[T, Sequence[T]]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, ctx, (), True)
        loc = ctx.get_loc(stream, pos)
        if rs:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if test(t):
                    return Recovered(
                        [
                            make_skip(
                                rs[0], t, cur + 1,
                                ctx.update_loc(stream, cur + 1), loc, cur - pos
                            ),
                        ], cur - pos, loc
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
            rs: RecoveryState) -> Result[T, Sequence[T]]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, ctx, (), True)
        loc = ctx.get_loc(stream, pos)
        if rs:
            reps: List[Repair[T, Sequence[T]]] = []
            if rs[0]:
                reps.append(
                    make_insert(rs[0], s, pos, ctx, loc, label_, expected)
                )
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    reps.append(
                        make_skip(
                            rs[0], t, cur + 1, ctx.update_loc(stream, cur + 1),
                            loc, cur - pos, expected
                        )
                    )
                    return Recovered(reps, cur - pos, loc, expected)
                cur += 1
            return Recovered(reps, None, loc, expected)
        return Error(loc, expected)

    return sym
