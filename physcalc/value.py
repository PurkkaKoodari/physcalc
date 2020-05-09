import re
from abc import ABC, abstractmethod
from fractions import Fraction
from typing import List, Optional

from physcalc.context import Context, Feature
from physcalc.operator import (OpPrecedence, OPERATOR_ADD, OPERATOR_SUBTRACT, OPERATOR_MULTIPLY, OPERATOR_DIVIDE,
                               Operator)
from physcalc.syntax import PART_NUMBER, Token
from physcalc.unit import Unit, NO_UNIT
from physcalc.util import MathParseError, MathEvalError, scientific, stringify_frac

NUMBER_RE = re.compile(PART_NUMBER)


class ExpressionPart(ABC):
    @abstractmethod
    def evaluate(self, _1, _2):
        pass

    @abstractmethod
    def stringify(self, context: Optional[Context], unit: Optional[Unit]):
        pass

    def __repr__(self):
        return f"<{type(self).__name__} {self.stringify(None, None)}>"

    def __str__(self):
        return self.stringify(None, None)

    def __add__(self, other):
        return OperatorExpression([self, other], [OPERATOR_ADD])

    def __radd__(self, other):
        return OperatorExpression([other, self], [OPERATOR_ADD])

    def __sub__(self, other):
        return OperatorExpression([self, other], [OPERATOR_SUBTRACT])

    def __rsub__(self, other):
        return OperatorExpression([other, self], [OPERATOR_SUBTRACT])

    def __mul__(self, other):
        return OperatorExpression([self, other], [OPERATOR_MULTIPLY])

    def __rmul__(self, other):
        return OperatorExpression([other, self], [OPERATOR_MULTIPLY])

    def __truediv__(self, other):
        return OperatorExpression([self, other], [OPERATOR_DIVIDE])

    def __rtruediv__(self, other):
        return OperatorExpression([other, self], [OPERATOR_DIVIDE])

    def __pow__(self, other):
        return PowerExpression([self, other])

    def __rpow__(self, other):
        return PowerExpression([other, self])

    def __neg__(self):
        return UnaryMinus.create(self)


class Value(ExpressionPart, Token):
    def __init__(self, number, unit):
        if isinstance(unit, tuple):
            self.number = number * unit[0]
            self.unit = unit[1]
        else:
            self.number = number
            self.unit = unit
        assert self.unit.multiplier == 1

    def stringify(self, context, unit):
        if context is not None and context.features[Feature.FRAC] and isinstance(self.number, Fraction):
            return stringify_frac(self.number, context) + " " + self.unit.name
        if unit is not None and unit is not NO_UNIT and self.unit.can_convert(unit):
            return scientific(self.number / unit.multiplier) + " " + unit.name
        if self.unit is NO_UNIT:
            return scientific(self.number)
        return scientific(self.number) + " " + self.unit.name

    def token_name(self):
        return "value " + self.__repr__()

    def evaluate(self, _1, _2):
        return self

    def __add__(self, other):
        if isinstance(other, Value):
            if other.unit != self.unit:
                raise MathEvalError("unit mismatch: cannot add " + str(self.unit) + " to " + str(other.unit))
            return Value(self.number + other.number, self.unit)
        return super().__add__(other)

    def __sub__(self, other):
        if isinstance(other, Value):
            if other.unit != self.unit:
                raise MathEvalError("unit mismatch: cannot subtract " + str(other.unit) + " from " + str(self.unit))
            return Value(self.number - other.number, self.unit)
        return super().__sub__(other)

    def __mul__(self, other):
        if isinstance(other, Value):
            return Value(self.number * other.number, self.unit * other.unit)
        return super().__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Value):
            return Value(self.number / other.number, self.unit / other.unit)
        return super().__truediv__(other)

    def __pow__(self, other):
        if isinstance(other, Value):
            if other.unit is not NO_UNIT:
                raise MathEvalError("cannot raise to power with unit " + str(other.unit))
            return Value(self.number ** other.number, self.unit ** other.number)
        return super().__pow__(other)

    def __neg__(self):
        return Value(-self.number, self.unit)

    @staticmethod
    def parse(text, _):
        num_match = NUMBER_RE.match(text)
        if num_match is None:
            number = 1
            unit_start = 0
        else:
            num = num_match.group(0)
            unit_start = num_match.end()
            if "/" in num:
                num, denom = num_match.group(0).split("/")
                number = Fraction(int(num), int(denom))
            elif "." in num:
                number = float(num)
            else:
                number = int(num)
        unit_mul, unit = Unit.parse(text[unit_start:]).to_si()
        return Value(number * unit_mul, unit)


def _stringify_expr(expr: ExpressionPart, max_paren_prec: OpPrecedence, context: Optional[Context], unit: Optional[Unit]):
    """Converts an expression to its code string.

    If the expression's precedence is at most max_paren_prec, the result is wrapped in parenthesis.
    """
    if ((isinstance(expr, OperatorExpression) and expr.prec <= max_paren_prec)
            or (isinstance(expr, PowerExpression) and OpPrecedence.POWER <= max_paren_prec)):
        return f"({expr.stringify(context, unit)})"
    return expr.stringify(context, unit)


class OperatorExpression(ExpressionPart):
    operators: List[Operator]
    subexprs: List[ExpressionPart]
    prec: OpPrecedence

    def __init__(self, subexprs, operators):
        assert 2 <= len(subexprs) == len(operators) + 1
        assert all(isinstance(expr, ExpressionPart) for expr in subexprs)
        self.prec = operators[0].prec
        assert self.prec in [OpPrecedence.ADD, OpPrecedence.MULTIPLY]
        assert all(oper.prec == self.prec for oper in operators)
        if isinstance(subexprs[0], OperatorExpression) and subexprs[0].prec == self.prec:
            self.subexprs = subexprs[0].subexprs
            self.operators = subexprs[0].operators
        else:
            self.subexprs = subexprs[:1]
            self.operators = []
        for expr, oper in zip(subexprs[1:], operators):
            if isinstance(expr, UnaryMinus):
                if self.prec == OpPrecedence.MULTIPLY:
                    expr = expr.subexpr
                    self.subexprs[0] = UnaryMinus.create(self.subexprs[0])
                elif self.prec == OpPrecedence.ADD:
                    oper = oper.inverse
                    expr = expr.subexpr
            self.operators.append(oper)
            if isinstance(expr, OperatorExpression) and expr.prec == self.prec:
                self.operators.extend(oper.distribute(expr_oper) for expr_oper in expr.operators)
                self.subexprs.extend(expr.subexprs)
            else:
                self.subexprs.append(expr)

    def stringify(self, context, unit):
        return _stringify_expr(self.subexprs[0], self.prec, context, unit) + "".join(
            " " + oper.name + " " + _stringify_expr(expr, self.prec, context, unit)
            for expr, oper in zip(self.subexprs[1:], self.operators)
        )

    def evaluate(self, context, var_stack):
        accum_value = None
        rest_operators = []
        rest_subexprs = []
        for oper, expr in zip([self.operators[0].positive] + self.operators, self.subexprs):
            expr_value = expr.evaluate(context, var_stack)
            if isinstance(expr_value, Value):
                if accum_value is None:
                    accum_value = Value(*oper.identity(expr_value))
                accum_value = oper.action(accum_value, expr_value)
            else:
                rest_operators.append(oper)
                rest_subexprs.append(expr_value)
        if not rest_subexprs:
            return accum_value
        if accum_value is None:
            return OperatorExpression(rest_subexprs, rest_operators[1:])
        rest_subexprs.insert(0, accum_value)
        return OperatorExpression(rest_subexprs, rest_operators)


class PowerExpression(ExpressionPart):
    subexprs: List[ExpressionPart]

    def __init__(self, subexprs: List[ExpressionPart]):
        self.subexprs = subexprs

    def stringify(self, context, unit):
        return " ^ ".join(_stringify_expr(expr, OpPrecedence.POWER, context, unit) for expr in self.subexprs)

    def evaluate(self, context, var_stack):
        accum_value = self.subexprs[-1].evaluate(context, var_stack)
        if not isinstance(accum_value, Value):
            return self
        for expr in self.subexprs[-2::-1]:
            expr_value = expr.evaluate(context, var_stack)
            if not isinstance(expr_value, Value):
                return self
            accum_value = expr_value ** accum_value
        return accum_value


class UnaryMinus(ExpressionPart):
    subexpr: ExpressionPart

    def __init__(self, subexpr):
        self.subexpr = subexpr

    def stringify(self, context, unit):
        return "-" + _stringify_expr(self.subexpr, OpPrecedence.POWER, context, unit)

    def evaluate(self, context, var_stack):
        return -self.subexpr.evaluate(context, var_stack)

    @staticmethod
    def create(subexpr: ExpressionPart):
        if isinstance(subexpr, UnaryMinus):
            return subexpr.subexpr
        if isinstance(subexpr, OperatorExpression):
            if subexpr.prec == OpPrecedence.ADD:
                subexprs = [UnaryMinus.create(subexpr.subexprs[0])] + subexpr.subexprs[1:]
                operators = [OPERATOR_SUBTRACT.distribute(oper) for oper in subexpr.operators]
                return OperatorExpression(subexprs, operators)
            if subexpr.prec == OpPrecedence.MULTIPLY:
                subexprs = [UnaryMinus.create(subexpr.subexprs[0])] + subexpr.subexprs[1:]
                return OperatorExpression(subexprs, subexpr.operators)
        return UnaryMinus(subexpr)


class Variable(ExpressionPart, Token):
    name: str

    def __init__(self, name: str):
        self.name = name

    def stringify(self, context, unit):
        return self.name

    def token_name(self):
        return "variable " + self.name

    def evaluate(self, context, var_stack):
        if self.name in var_stack or self.name not in context.variables:
            return self
        value = context.variables[self.name]
        # prevent stack overflows in case of self-referential expressions
        if self.name not in var_stack:
            var_stack.append(self.name)
            value = value.evaluate(context, var_stack)
            var_stack.pop()
        return value

    @staticmethod
    def parse(text, _):
        return Variable(text)


class Output(ExpressionPart, Token):
    index: int

    def __init__(self, index: int):
        self.index = index

    def evaluate(self, context, var_stack):
        return context.outputs[self.index - 1].evaluate(context, var_stack)

    def stringify(self, context, unit):
        return f"[{self.index}]"

    def token_name(self):
        return f"output ref [{self.index}]"

    @staticmethod
    def parse(text, context):
        index = int(text[1:-1])
        if not 1 <= index <= len(context.outputs):
            raise MathParseError(f"no such result [{index}]")
        return Output(index)
