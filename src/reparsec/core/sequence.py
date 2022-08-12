from typing import Callable, Iterable, List, Optional, Sequence, Sized, TypeVar

from .parser import ParseFastFn, ParseFn, ParseFns
from .repair import Repair, make_insert, make_pending_skip, make_skip
from .result import Error, Ok, Recovered, Result, SimpleResult
from .types import Ctx

A = TypeVar("A")


def _eof_fast() -> ParseFastFn[Sized, None]:
    def eof(
            stream: Sized, pos: int,
            ctx: Ctx[Sized]) -> SimpleResult[None, Sized]:
        if pos == len(stream):
            return Ok(None, pos, ctx)
        return Error(ctx.get_loc(stream, pos), ["end of file"])

    return eof


def _eof() -> ParseFn[Sized, None]:
    def eof(
            stream: Sized, pos: int, ctx: Ctx[Sized], ins: int,
            rem: Optional[int]) -> Result[None, Sized]:
        if pos == len(stream):
            return Ok(None, pos, ctx)
        if rem is None:
            return Error(ctx.get_loc(stream, pos), ["end of file"])
        loc = ctx.get_loc(stream, pos)
        sl = len(stream)
        return Recovered(
            [
                make_pending_skip(
                    ins, None, sl, ctx, loc, sl - pos, ["end of file"]
                ),
            ], None, loc, ["end of file"]
        )

    return eof


def eof() -> ParseFns[Sized, None]:
    return ParseFns(_eof_fast(), _eof())


def _satisfy_fast(test: Callable[[A], bool]) -> ParseFastFn[Sequence[A], A]:
    def satisfy(
            stream: Sequence[A], pos: int,
            ctx: Ctx[Sequence[A]]) -> SimpleResult[A, Sequence[A]]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, ctx, (), True)
        return Error(ctx.get_loc(stream, pos))

    return satisfy


def _satisfy(test: Callable[[A], bool]) -> ParseFn[Sequence[A], A]:
    def satisfy(
            stream: Sequence[A], pos: int, ctx: Ctx[Sequence[A]], ins: int,
            rem: Optional[int]) -> Result[A, Sequence[A]]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, ctx, (), True)
        if rem is None:
            return Error(ctx.get_loc(stream, pos))
        loc = ctx.get_loc(stream, pos)
        cur = pos + 1
        while cur < len(stream):
            t = stream[cur]
            if test(t):
                return Recovered(
                    [
                        make_skip(
                            ins, t, cur + 1, ctx.update_loc(stream, cur + 1),
                            loc, cur - pos
                        ),
                    ], cur - pos, loc
                )
            cur += 1
        return Error(loc)

    return satisfy


def satisfy(test: Callable[[A], bool]) -> ParseFns[Sequence[A], A]:
    return ParseFns(_satisfy_fast(test), _satisfy(test))


def _sym_fast(s: A, expected: Iterable[str]) -> ParseFastFn[Sequence[A], A]:
    def sym(
            stream: Sequence[A], pos: int,
            ctx: Ctx[Sequence[A]]) -> SimpleResult[A, Sequence[A]]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, ctx, (), True)
        return Error(ctx.get_loc(stream, pos), expected)

    return sym


def _sym(s: A, label: str, expected: Iterable[str]) -> ParseFn[Sequence[A], A]:
    def sym(
            stream: Sequence[A], pos: int, ctx: Ctx[Sequence[A]], ins: int,
            rem: Optional[int]) -> Result[A, Sequence[A]]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, ctx, (), True)
        if rem is None:
            return Error(ctx.get_loc(stream, pos), expected)
        loc = ctx.get_loc(stream, pos)
        reps: List[Repair[A, Sequence[A]]] = []
        if rem:
            reps.append(make_insert(rem, s, pos, ctx, loc, label, expected))
        cur = pos + 1
        while cur < len(stream):
            t = stream[cur]
            if t == s:
                reps.append(
                    make_skip(
                        ins, t, cur + 1, ctx.update_loc(stream, cur + 1), loc,
                        cur - pos, expected
                    )
                )
                return Recovered(reps, cur - pos, loc, expected)
            cur += 1
        return Recovered(reps, None, loc, expected)

    return sym


def sym(s: A, label: Optional[str]) -> ParseFns[Sequence[A], A]:
    if label is None:
        label_ = repr(s)
    else:
        label_ = label
    expected = [label_]

    return ParseFns(_sym_fast(s, expected), _sym(s, label_, expected))
