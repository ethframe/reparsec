from functools import reduce
from typing import Callable, List, Tuple, TypeVar

from .parser import Parser

T = TypeVar("T")
V = TypeVar("V")
U = TypeVar("U")


def infix_left(
        arg: Parser[T, V], op: Parser[T, U],
        fn: Callable[[U, V, V], V]) -> Parser[T, V]:
    return (
        arg + (op + arg).many()
    ).fmap(lambda v: reduce(lambda t, o: fn(o[0], t, o[1]), v[1], v[0]))


def infix_right(
        arg: Parser[T, V], op: Parser[T, U],
        fn: Callable[[U, V, V], V]) -> Parser[T, V]:
    def build(v: Tuple[V, List[Tuple[U, V]]]) -> V:
        head, tail = v
        rassoc: List[Tuple[V, U]] = []
        for op, arg in tail:
            rassoc.append((head, op))
            head = arg
        return reduce(lambda t, o: fn(o[1], o[0], t), reversed(rassoc), head)

    return (arg + (op + arg).many()).fmap(build)


def infix_non(
        arg: Parser[T, V], op: Parser[T, U],
        fn: Callable[[U, V, V], V]) -> Parser[T, V]:
    return (
        arg + (op + arg).maybe()
    ).fmap(lambda v: v[0] if v[1] is None else fn(v[1][0], v[0], v[1][1]))


def prefix(
        op: Parser[T, U], arg: Parser[T, V],
        fn: Callable[[U, V], V]) -> Parser[T, V]:
    return (
        op.many() + arg
    ).fmap(lambda v: reduce(lambda t, o: fn(o, t), v[0], v[1]))


def postfix(
        arg: Parser[T, V], op: Parser[T, U],
        fn: Callable[[V, U], V]) -> Parser[T, V]:
    return (
        arg + op.many()
    ).fmap(lambda v: reduce(fn, v[1], v[0]))
