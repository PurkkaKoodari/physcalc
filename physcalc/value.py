import itertools
import re
from abc import ABC, abstractmethod
from fractions import Fraction

from physcalc.context import FEATURE_FRAC, FEATURE_GRAPHIC
from physcalc.syntax import SUBTOKEN_NUMBER, Token
from physcalc import util
from physcalc.util import MathParseError, MathEvalError

DIV_SEPARATOR = 0
UNIT_AMPERE = 1
UNIT_KILOGRAM = 2
UNIT_METER = 3
UNIT_SECOND = 4
UNIT_KELVIN = 5
UNIT_MOLE = 6
UNIT_CANDELA = 7

UNIT_MAP = {
    UNIT_METER: "m",
    UNIT_KILOGRAM: "kg",
    UNIT_SECOND: "s",
    UNIT_KELVIN: "K",
    UNIT_AMPERE: "A",
    UNIT_MOLE: "mol",
    UNIT_CANDELA: "cd",
}

MUL_PREFIXES = [
    ("da", Fraction(10, 1)),
    ("h", Fraction(100, 1)),
    ("k", Fraction(1000, 1)),
    ("M", Fraction(1000 ** 2, 1)),
    ("G", Fraction(1000 ** 3, 1)),
    ("T", Fraction(1000 ** 4, 1)),
    ("P", Fraction(1000 ** 5, 1)),
    ("E", Fraction(1000 ** 6, 1)),
    ("Z", Fraction(1000 ** 7, 1)),
    ("Y", Fraction(1000 ** 8, 1)),
    ("d", Fraction(1, 10)),
    ("c", Fraction(1, 100)),
    ("m", Fraction(1, 1000)),
    ("u", Fraction(1, 1000) ** 2),
    ("μ", Fraction(1, 1000) ** 2),
    ("n", Fraction(1, 1000) ** 3),
    ("p", Fraction(1, 1000) ** 4),
    ("f", Fraction(1, 1000) ** 5),
    ("a", Fraction(1, 1000) ** 6),
    ("z", Fraction(1, 1000) ** 7),
    ("y", Fraction(1, 1000) ** 8),
    ("", Fraction(1, 1)),
]

WHITESPACE_RE = re.compile(r"\s+")
NUMBER_RE = re.compile(SUBTOKEN_NUMBER)

def _parse_unit_part(text):
    try:
        result = NO_UNIT
        total_mul = Fraction(1, 1)
        parts = WHITESPACE_RE.split(text)
        if parts == ["1"]:
            return total_mul, result
        for part in parts:
            if not part:
                continue
            unit, power = util.parse_power(part)
            if unit not in Unit.name_registry:
                mul_text, mul = next(prefix for prefix in MUL_PREFIXES if unit.startswith(prefix[0]))
                unit = unit[len(mul_text):]
            else:
                mul = 1
            unit = Unit.name_registry[unit]
            power = int(power)
            for _ in range(power):
                result *= unit
                total_mul *= mul
            for _ in range(-power):
                result /= unit
                total_mul /= mul
        return total_mul, result
    except ValueError as ex:
        raise MathParseError("invalid number") from None
    except KeyError as ex:
        raise MathParseError("unknown unit " + str(ex.args[0])) from None

def _cancel_unit_parts(num, denom):
    num_list = sorted(num)
    denom_list = sorted(denom)
    num_i = denom_i = 0
    while num_i < len(num_list) and denom_i < len(denom_list):
        num_unit = num_list[num_i]
        denom_unit = denom_list[denom_i]
        if num_unit == denom_unit:
            del num_list[num_i]
            del denom_list[denom_i]
        elif num_unit < denom_unit:
            num_i += 1
        else:
            denom_i += 1
    return tuple(num_list), tuple(denom_list)

def _generate_unit_part(part):
    if not part:
        return "1", 1
    units = []
    weight = 1
    for unit, power in itertools.groupby(part):
        units.append(UNIT_MAP[unit] + util.generate_sup_power(util.iterlen(power)))
        weight *= 2
    return " ".join(units), weight

def _generate_unit_names(num, denom):
    if not num and not denom:
        return [("", 0)]
    basic_name, basic_weight = _generate_unit_part(num)
    if denom:
        basic_denom, denom_weight = _generate_unit_part(denom)
        basic_name += " / " + basic_denom
        basic_weight *= denom_weight
    results = [(basic_name, basic_weight)]
    for test_denom in Unit.special_units:
        if (num, denom) == (test_denom.denom, test_denom.num):
            results.append(("1 / " + test_denom.name, test_denom.weight * 2))
    for test1, test2 in itertools.combinations(Unit.special_units, 2):
        if (num, denom) == _cancel_unit_parts(test1.num + test2.num, test1.denom + test2.denom):
            results.append((test1.name + " " + test2.name, test1.weight * test2.weight))
    for test_num, test_denom in itertools.permutations(Unit.special_units, 2):
        if (num, denom) == _cancel_unit_parts(test_num.num + test_denom.denom, test_num.denom + test_denom.num):
            results.append((test_num.name + " / " + test_denom.name, test_num.weight * test_denom.weight))
    # print("TODO: " + "\nTODO: ".join(a[0]+" for "+str(a[1]) for a in results) + "\n")
    return results

def _generate_unit_name(num, denom):
    return min(_generate_unit_names(num, denom), key=lambda pair: pair[1])[0]

def _mul_list_frac(lst, frac):
    out = []
    for i in range(0, len(lst), frac.denominator):
        for j in range(1, frac.denominator):
            if i + j > len(lst) or lst[i + j] != lst[i]:
                raise ValueError
        for j in range(frac.numerator):
            out.append(lst[i])
    return out

def _stringify_frac(frac, context):
    if context is not None and context.features[FEATURE_GRAPHIC]:
        raise NotImplementedError
    if frac.denominator == 1:
        return str(frac.numerator)
    return "%s/%s" % (frac.numerator, frac.denominator)

class Unit:
    part_registry = {}
    name_registry = {}
    special_units = []
    def __init__(self, special_name, num, denom, weight=1000, variable=None):
        key = num + (DIV_SEPARATOR,) + denom
        if key in Unit.part_registry:
            raise ValueError("unit already registered")
        Unit.part_registry[key] = self
        self.name = special_name if special_name is not None else _generate_unit_name(num, denom)
        self.num = num
        self.denom = denom
        self.weight = weight
        self.variable = variable
    @staticmethod
    def register(special_name, weight, variable, num, denom=()):
        num, denom = _cancel_unit_parts(num, denom)
        created = Unit(special_name, num, denom, weight, variable)
        if special_name is not None:
            Unit.special_units.append(created)
            Unit.name_registry[special_name] = created
        return created
    @staticmethod
    def from_parts(num, denom):
        num, denom = _cancel_unit_parts(num, denom)
        key = num + (DIV_SEPARATOR,) + denom
        if key in Unit.part_registry:
            return Unit.part_registry[key]
        return Unit(None, num, denom)
    @staticmethod
    def parse(name):
        num, denom = name.split("/") if "/" in name else (name, "")
        num_mul, num = _parse_unit_part(num)
        denom_mul, denom = _parse_unit_part(denom)
        return num_mul / denom_mul, num / denom
    def __mul__(self, other):
        return Unit.from_parts(self.num + other.num, self.denom + other.denom)
    def __truediv__(self, other):
        return Unit.from_parts(self.num + other.denom, self.denom + other.num)
    def __rtruediv__(self, other):
        if other == 1:
            return NO_UNIT / self
        return NotImplemented
    def __pow__(self, other):
        if other == 0 or self is NO_UNIT:
            return NO_UNIT
        if isinstance(other, Fraction):
            try:
                return Unit.from_parts(_mul_list_frac(self.num, other), _mul_list_frac(self.denom, other))
            except ValueError:
                raise MathEvalError("cannot raise %s to power %s" % (self, other))
        if not isinstance(other, int) and not (isinstance(other, float) and other.is_integer()):
            raise MathEvalError("cannot raise %s to non-integer power" % self)
        return Unit.from_parts(self.num * int(other), self.denom * int(other))
    def __eq__(self, other):
        return self is other or (self.num == other.num and self.denom == other.denom)
    def __repr__(self):
        return self.stringify(None)
    def stringify(self, _):
        return self.name
    def names(self):
        return [name for name, _ in sorted(_generate_unit_names(self.num, self.denom), key=lambda pair: pair[1])]

NO_UNIT = Unit.register(None, 2, "number", ())
Unit.register("A", 2, "electric current", (UNIT_AMPERE,))
Unit.register("kg", 2, "mass", (UNIT_KILOGRAM,))
Unit.register("m", 2, "distance", (UNIT_METER,))
Unit.register("s", 2, "time", (UNIT_SECOND,))
Unit.register("K", 2, "temperature", (UNIT_KELVIN,))
Unit.register("mol", 2, "amount of substance", (UNIT_MOLE,))
Unit.register("cd", 2, "luminous intensity", (UNIT_CANDELA,))

Unit.register("N", 3, "force", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND, UNIT_SECOND))
Unit.register("J", 3, "energy", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND))
Unit.register("Pa", 4, "pressure", (UNIT_KILOGRAM,), (UNIT_SECOND, UNIT_SECOND, UNIT_METER))
Unit.register("W", 4, "power", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND))

Unit.register("C", 3, "electric charge", (UNIT_AMPERE, UNIT_SECOND))
Unit.register("V", 3, "voltage", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE))
Unit.register("F", 4, "capacitance", (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE, UNIT_AMPERE), (UNIT_KILOGRAM, UNIT_METER, UNIT_METER))
Unit.register("\u03A9", 4, "resistance", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE, UNIT_AMPERE))
Unit.register("S", 5, "conductance", (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE, UNIT_AMPERE), (UNIT_KILOGRAM, UNIT_METER, UNIT_METER))
Unit.register("Wb", 4, "magnetic flux", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE))
Unit.register("T", 4, "magnetic field", (UNIT_KILOGRAM,), (UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE))
Unit.register("H", 4, "inductance", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE, UNIT_AMPERE))

Unit.register("lux", 3, "illuminance", (UNIT_CANDELA,), (UNIT_METER, UNIT_METER))
Unit.register("Hz", 4, "frequency", (), (UNIT_SECOND,))

Unit.register(None, 3, "area", (UNIT_METER, UNIT_METER))
Unit.register(None, 4, "volume", (UNIT_METER, UNIT_METER, UNIT_METER))
Unit.register(None, 3, "speed", (UNIT_METER,), (UNIT_SECOND,))
Unit.register(None, 4, "acceleration", (UNIT_METER,), (UNIT_SECOND, UNIT_SECOND))
Unit.register(None, 4, "momentum", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND,))
Unit.register(None, 5, "angular momentum", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND,))
Unit.register(None, 5, "moment of inertia", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), ())
Unit.register(None, 4, "electric field", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE))

Unit.register(None, 5, "thermal conductivity", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN))
Unit.register(None, 5, "thermal capacity", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN))
Unit.register(None, 5, "specific thermal capacity", (UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN))
Unit.register(None, 5, "molar thermal capacity", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN, UNIT_MOLE))

Unit.register(None, 5, "molar mass", (UNIT_KILOGRAM,), (UNIT_MOLE,))
Unit.register(None, 5, "concentration", (UNIT_MOLE,), (UNIT_METER, UNIT_METER, UNIT_METER))

class ExpressionPart(ABC):
    @abstractmethod
    def evaluate(self, _1, _2):
        pass
    @abstractmethod
    def stringify(self, context):
        pass
    def __repr__(self):
        return self.stringify(None)
    def __add__(self, other):
        return Expression([self, other], [OPERATOR_ADD])
    def __radd__(self, other):
        return Expression([other, self], [OPERATOR_ADD])
    def __sub__(self, other):
        return Expression([self, other], [OPERATOR_SUBTRACT])
    def __rsub__(self, other):
        return Expression([other, self], [OPERATOR_SUBTRACT])
    def __mul__(self, other):
        return Expression([self, other], [OPERATOR_MULTIPLY])
    def __rmul__(self, other):
        return Expression([other, self], [OPERATOR_MULTIPLY])
    def __truediv__(self, other):
        return Expression([self, other], [OPERATOR_DIVIDE])
    def __rtruediv__(self, other):
        return Expression([other, self], [OPERATOR_DIVIDE])
    def __pow__(self, other):
        return PowerExpression([self, other])
    def __rpow__(self, other):
        return PowerExpression([other, self])
    def __neg__(self):
        return UnaryMinus(self)

class Value(ExpressionPart, Token):
    def __init__(self, number, unit):
        if isinstance(unit, tuple):
            self.number = number * unit[0]
            self.unit = unit[1]
        else:
            self.number = number
            self.unit = unit
    def stringify(self, context):
        if context is not None and context.features[FEATURE_FRAC] and isinstance(self.number, Fraction):
            return _stringify_frac(self.number, context) + " " + self.unit.stringify(context)
        if self.unit is NO_UNIT:
            return util.scientific(self.number)
        return util.scientific(self.number) + " " + self.unit.stringify(context)
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
        num_match = re.match(SUBTOKEN_NUMBER, text)
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
        unit_mul, unit = Unit.parse(text[unit_start:])
        return Value(number * unit_mul, unit)

def _str_expr(expr, max_paren_prec, context):
    if ((isinstance(expr, Expression) and expr.prec <= max_paren_prec)
            or (isinstance(expr, PowerExpression) and PREC_POWER <= max_paren_prec)):
        return "(" + expr.stringify(context) + ")"
    return expr.stringify(context)

class Expression(ExpressionPart):
    def __init__(self, subexprs, operators):
        assert 2 <= len(subexprs) == len(operators) + 1
        assert all(isinstance(expr, ExpressionPart) for expr in subexprs)
        assert all(oper.prec in [PREC_ADD, PREC_MULTIPLY] for oper in operators)
        self.prec = operators[0].prec
        if isinstance(subexprs[0], Expression) and subexprs[0].prec == self.prec:
            self.subexprs = subexprs[0].subexprs
            self.operators = subexprs[0].operators
        else:
            self.subexprs = subexprs[:1]
            self.operators = []
        for expr, oper in zip(subexprs[1:], operators):
            self.operators.append(oper)
            if isinstance(expr, Expression) and expr.prec == self.prec:
                self.operators.extend(oper.merge(expr_oper) for expr_oper in expr.operators)
                self.subexprs.extend(expr.subexprs)
            else:
                self.subexprs.append(expr)
    def stringify(self, context):
        return _str_expr(self.subexprs[0], self.prec, context) + "".join(
            " " + oper.name + " " + _str_expr(expr, self.prec, context)
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
                    accum_value = oper.identity(expr_value)
                accum_value = oper.action(accum_value, expr_value)
            else:
                rest_operators.append(oper)
                rest_subexprs.append(expr_value)
        if not rest_subexprs:
            return accum_value
        if accum_value is None:
            return Expression(rest_subexprs, rest_operators[1:])
        rest_subexprs.insert(0, accum_value)
        return Expression(rest_subexprs, rest_operators)
    # TODO: remove?
    # @staticmethod
    # def create(subexprs, operators):
    #     if len(subexprs) == 1:
    #         return subexprs[0]
    #     return Expression(subexprs, operators)

class PowerExpression(ExpressionPart):
    def __init__(self, subexprs):
        self.subexprs = subexprs
    def stringify(self, context):
        return " ^ ".join(_str_expr(expr, PREC_POWER, context) for expr in self.subexprs)
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
    # TODO: remove?
    # @staticmethod
    # def create(subexprs):
    #     if len(subexprs) == 1:
    #         return subexprs[0]
    #     return PowerExpression(subexprs)

class UnaryMinus(ExpressionPart):
    def __init__(self, subexpr):
        self.subexpr = subexpr
    def stringify(self, context):
        return "-" + _str_expr(self.subexpr, PREC_POWER, context)
    def evaluate(self, context, var_stack):
        return -self.subexpr.evaluate(context, var_stack)
    @staticmethod
    def create(subexpr):
        if isinstance(subexpr, UnaryMinus):
            return subexpr.subexpr
        if isinstance(subexpr, Expression) and subexpr.prec == PREC_ADD:
            subexprs = [UnaryMinus.create(subexpr.subexprs[0])] + subexpr.subexprs[1:]
            operators = [OPERATOR_SUBTRACT.merge(oper) for oper in subexpr.operators]
            return Expression(subexprs, operators)
        return UnaryMinus(subexpr)

class Variable(ExpressionPart, Token):
    def __init__(self, name):
        self.name = name
    def stringify(self, _):
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
    def __init__(self, index):
        self.index = index
    def evaluate(self, context, var_stack):
        return context.outputs[self.index - 1].evaluate(context, var_stack)
    def stringify(self, _):
        return "[" + str(self.index) + "]"
    def token_name(self):
        return "output ref [" + str(self.index) + "]"
    @staticmethod
    def parse(text, context):
        index = int(text[1:-1])
        if not 1 <= index <= len(context.outputs):
            raise MathParseError("no such result [" + str(index) + "]")
        return Output(index)

class Operator(Token):
    registry = {}
    def __init__(self, name, prec, action, is_unary):
        self.name = name
        self.prec = prec
        self.action = action
        self.inverse = None
        self.is_unary = is_unary
        self.positive = self
        self.identity = None
    def __repr__(self):
        return "<operator " + self.name + ">"
    def token_name(self):
        return "operator " + self.name
    def merge(self, other):
        return self.inverse if other is self else self
    @staticmethod
    def register(names, prec, action, is_unary=False):
        oper = Operator(names[0], prec, action, is_unary)
        for name in names:
            Operator.registry[name] = oper
        return oper
    @staticmethod
    def parse(name, _):
        return Operator.registry[name]

PREC_ADD = 1
PREC_MULTIPLY = 2
PREC_POWER = 3

OPERATOR_ADD = Operator.register(["+"], PREC_ADD, lambda a, b: a + b)
OPERATOR_SUBTRACT = Operator.register(["-"], PREC_ADD, lambda a, b: a - b, True)
OPERATOR_ADD.inverse = OPERATOR_SUBTRACT
OPERATOR_SUBTRACT.inverse = OPERATOR_ADD
OPERATOR_SUBTRACT.positive = OPERATOR_ADD
OPERATOR_ADD.identity = OPERATOR_SUBTRACT.identity = lambda other: Value(0, other.unit)
OPERATOR_MULTIPLY = Operator.register(["*", "·", "×"], PREC_MULTIPLY, lambda a, b: a * b)
OPERATOR_DIVIDE = Operator.register(["/", "÷"], PREC_MULTIPLY, lambda a, b: a / b)
OPERATOR_MULTIPLY.inverse = OPERATOR_DIVIDE
OPERATOR_DIVIDE.inverse = OPERATOR_MULTIPLY
OPERATOR_DIVIDE.positive = OPERATOR_MULTIPLY
OPERATOR_MULTIPLY.identity = OPERATOR_DIVIDE.identity = lambda _: Value(1, NO_UNIT)
OPERATOR_POWER = Operator.register(["^", "**"], PREC_POWER, lambda a, b: a ** b)
