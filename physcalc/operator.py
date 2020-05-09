from enum import IntEnum
from numbers import Real
from typing import Callable, Optional, Tuple, TYPE_CHECKING

from physcalc.syntax import Token
from physcalc.unit import NO_UNIT, Unit

if TYPE_CHECKING:
    from physcalc.value import Value


class OpPrecedence(IntEnum):
    ADD = 1
    MULTIPLY = 2
    POWER = 3


class Operator(Token):
    registry = {}

    name: str
    prec: OpPrecedence
    action: "Callable[[Value, Value], Value]"
    is_unary: bool
    inverse: "Optional[Operator]"
    positive: "Operator"
    identity: "Optional[Callable[[Value], Tuple[Real, Unit]]]"

    def __init__(self, name, prec, action, is_unary):
        self.name = name
        self.prec = prec
        self.action = action
        self.is_unary = is_unary
        self.inverse = None
        self.positive = self
        self.identity = None

    def __repr__(self):
        return f"<operator {self.name}>"

    def token_name(self):
        return f"operator {self.name}"

    def distribute(self, other: "Operator") -> "Operator":
        return self.positive if other is self else self.positive.inverse

    @staticmethod
    def register(names, prec, action, is_unary=False):
        oper = Operator(names[0], prec, action, is_unary)
        for name in names:
            Operator.registry[name] = oper
        return oper

    @staticmethod
    def parse(name, _):
        return Operator.registry[name]


OPERATOR_ADD = Operator.register(["+"], OpPrecedence.ADD, lambda a, b: a + b)
OPERATOR_SUBTRACT = Operator.register(["-"], OpPrecedence.ADD, lambda a, b: a - b, True)
OPERATOR_MULTIPLY = Operator.register(["*", "·", "×"], OpPrecedence.MULTIPLY, lambda a, b: a * b)
OPERATOR_DIVIDE = Operator.register(["/", "÷"], OpPrecedence.MULTIPLY, lambda a, b: a / b)
OPERATOR_POWER = Operator.register(["^", "**"], OpPrecedence.POWER, lambda a, b: a ** b)

OPERATOR_ADD.inverse = OPERATOR_SUBTRACT
OPERATOR_SUBTRACT.inverse = OPERATOR_ADD
OPERATOR_SUBTRACT.positive = OPERATOR_ADD

OPERATOR_ADD.identity = OPERATOR_SUBTRACT.identity = lambda other: (0, other.unit)

OPERATOR_MULTIPLY.inverse = OPERATOR_DIVIDE
OPERATOR_DIVIDE.inverse = OPERATOR_MULTIPLY
OPERATOR_DIVIDE.positive = OPERATOR_MULTIPLY

OPERATOR_MULTIPLY.identity = OPERATOR_DIVIDE.identity = lambda _: (1, NO_UNIT)
