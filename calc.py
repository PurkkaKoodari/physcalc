import math
import re
import itertools
from fractions import Fraction
import atexit
import os

APPLICATION = "PhysCalc"
VERSION = "0.1"

LAUNCH_CREDITS = APPLICATION + " REPL " + VERSION + "\nType !help for help"

DIV_SEPARATOR = 0
UNIT_AMPERE = 1
UNIT_KILOGRAM = 2
UNIT_METER = 3
UNIT_SECOND = 4
UNIT_KELVIN = 5
UNIT_MOLE = 6
UNIT_CANDELA = 7
UNIT_RADIAN = 8

UNIT_MAP = {
    UNIT_METER: "m",
    UNIT_KILOGRAM: "kg",
    UNIT_SECOND: "s",
    UNIT_KELVIN: "K",
    UNIT_AMPERE: "A",
    UNIT_MOLE: "mol",
    UNIT_CANDELA: "cd",
    UNIT_RADIAN: "r",
}

MUL_PREFIXES = [
    ("da", 10),
    ("h", 100),
    ("k", 1000),
    ("M", 1000 ** 2),
    ("G", 1000 ** 3),
    ("T", 1000 ** 4),
    ("P", 1000 ** 5),
    ("E", 1000 ** 6),
    ("Z", 1000 ** 7),
    ("Y", 1000 ** 8),
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
    ("", 1),
]

SUP_CHARS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"
DECIMAL_TO_SUP = dict(zip(map(ord, "0123456789-"), SUP_CHARS))
SUP_TO_DECIMAL = dict(zip(map(ord, SUP_CHARS), "0123456789-"))

# The Greek alphabet mostly matches the Latin alphabet by position.
# Exceptions:
#  - \c = γ (gamma, to keep first 5 characters consistent)
#  - \j = η (eta, would be at \i but iota matches the looks more)
#  - \q = ψ (psi, no direct match)
#  - \v = θ (theta, no direct match)
#  - \w and \y unused
LATIN_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
GREEK_ALPHABET = "αβγδεφγχιηκλμνωπψρστυθ-ξ-ζΑΒΓΔΕΦΓΧΙΗΚΛΜΝΩΠΨΡΣΤΥΘ-Ξ-Ζ"

MULTIPLY_RE = re.compile(r"[*\s]+")

MAX_UNIT_WEIGHT = 5

ESCAPE_REGEX = re.compile(r"\\.")

SUBTOKEN_POSITIVE_DECIMAL = r"(?:\d+(?:\.\d*)?|\.\d+)"
SUBTOKEN_DECIMAL = r"-?" + SUBTOKEN_POSITIVE_DECIMAL
SUBTOKEN_POSITIVE_FRACTION = r"\d+(?:\s*/\s*\d+)?"
SUBTOKEN_FRACTION = r"-?" + SUBTOKEN_POSITIVE_FRACTION
SUBTOKEN_POSITIVE_NUMBER = r"\d+(?:\s*/\s*\d+|\.\d*)?|\.\d+"
SUBTOKEN_NUMBER = r"-?(?:" + SUBTOKEN_POSITIVE_NUMBER + r")"

SUBTOKEN_VARIABLE_NAME = r"[A-Za-z\u0370-\u03FF]+"
SUBTOKEN_UNIT_NAME = r"[A-Za-z\u0370-\u03FF\s]+"
SUBTOKEN_SUBSCRIPT_CONTENT = r"[A-Za-z0-9\u0370-\u03FF]+"

SUBTOKEN_POWER = r"\^" + SUBTOKEN_DECIMAL + r"|\u207B?[\xB2\xB3\xB9\u2070\u2074-\u2079]+"
SUBTOKEN_SUBSCRIPT = r"_" + SUBTOKEN_SUBSCRIPT_CONTENT

SUBTOKEN_UNIT_POWER = SUBTOKEN_UNIT_NAME + r"(?:" + SUBTOKEN_POWER + r")?"
SUBTOKEN_UNIT = r"(?:" + SUBTOKEN_UNIT_POWER + r")+(?:/(?:" + SUBTOKEN_UNIT_POWER + r")+)?"

TOKEN_OUTPUT = r"\[\d+\]"
TOKEN_VARIABLE = r"\$" + SUBTOKEN_VARIABLE_NAME + r"(?:" + SUBTOKEN_SUBSCRIPT + r")?"
TOKEN_VALUE = r"(?:" + SUBTOKEN_POSITIVE_NUMBER + r")(?:" + SUBTOKEN_UNIT + r")?"
TOKEN_OPERATOR = r"\*\*|[<=>:]=|[+\-*\xB7\xD7/\xF7^<=>\u2260\u2264\u2265]"
TOKEN_PARENTHESIS = "[()]"

class MathParseError(Exception):
    pass

class MathEvalError(Exception):
    pass

def _parse_unit_part(text):
    try:
        result = Unit.from_parts((), ())
        total_mul = 1
        parts = MULTIPLY_RE.split(text)
        if parts == ["1"]:
            return total_mul, result
        for part in parts:
            if not part:
                continue
            if "^" in part:
                unit, power = part.split("^", 1)
            elif part[-1] in SUP_CHARS:
                unit = part.rstrip(SUP_CHARS)
                power = part[len(unit):].translate(SUP_TO_DECIMAL)
            else:
                unit = part
                power = 1
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

def _iterlen(itr):
    return sum(1 for _ in itr)

def _generate_sup_power(power):
    return str(power).translate(DECIMAL_TO_SUP) if power != 1 else ""

def _generate_unit_part(part):
    if not part:
        return "1", 1
    units = []
    weight = 1
    for unit, power in itertools.groupby(part):
        units.append(UNIT_MAP[unit] + _generate_sup_power(_iterlen(power)))
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
    print("TODO: " + "\nTODO: ".join(a[0]+" for "+str(a[1]) for a in results) + "\n")
    return results

def _generate_unit_name(num, denom):
    return min(_generate_unit_names(num, denom), key=lambda pair: pair[1])[0]

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
            return Unit.from_parts((), ()) / self
        return NotImplemented
    def __pow__(self, other):
        if other == 0:
            return Unit.from_parts((), ())
        return Unit.from_parts(self.num * other, self.denom * other)
    def __eq__(self, other):
        return self is other or (self.num == other.num and self.denom == other.denom)
    def __repr__(self):
        return self.name
    def names(self):
        return [name for name, _ in sorted(_generate_unit_names(self.num, self.denom), key=lambda pair: pair[1])]

Unit.register(None, 2, "number", ())
Unit.register("A", 2, "electric current", (UNIT_AMPERE,))
Unit.register("kg", 2, "mass", (UNIT_KILOGRAM,))
Unit.register("m", 2, "distance", (UNIT_METER,))
Unit.register("s", 2, "time", (UNIT_SECOND,))
Unit.register("K", 2, "temperature", (UNIT_KELVIN,))
Unit.register("mol", 2, "amount of substance", (UNIT_MOLE,))
Unit.register("cd", 2, "luminous intensity", (UNIT_CANDELA,))
Unit.register("r", 2, "angle", (UNIT_RADIAN,))

Unit.register("sr", 2, "solid angle", (UNIT_RADIAN, UNIT_RADIAN))

Unit.register("N", 3, "force", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND, UNIT_SECOND))
Unit.register("J", 3, "energy", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND))
Unit.register("Pa", 4, "pressure", (UNIT_KILOGRAM,), (UNIT_SECOND, UNIT_SECOND, UNIT_METER, UNIT_METER))
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
Unit.register("lm", 3, "luminous flux", (UNIT_CANDELA, UNIT_RADIAN, UNIT_RADIAN))
Unit.register("Hz", 4, "frequency", (), (UNIT_SECOND,))

Unit.register(None, 3, "area", (UNIT_METER, UNIT_METER))
Unit.register(None, 4, "volume", (UNIT_METER, UNIT_METER, UNIT_METER))
Unit.register(None, 3, "speed", (UNIT_METER,), (UNIT_SECOND,))
Unit.register(None, 4, "acceleration", (UNIT_METER,), (UNIT_SECOND, UNIT_SECOND))
Unit.register(None, 4, "momentum", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND,))
Unit.register(None, 3, "torque", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_RADIAN))
Unit.register(None, 4, "electric field", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_AMPERE))

Unit.register(None, 5, "thermal conductivity", (UNIT_KILOGRAM, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN))
Unit.register(None, 5, "thermal capacity", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN))
Unit.register(None, 5, "specific thermal capacity", (UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN))
Unit.register(None, 5, "molar thermal capacity", (UNIT_KILOGRAM, UNIT_METER, UNIT_METER), (UNIT_SECOND, UNIT_SECOND, UNIT_KELVIN, UNIT_MOLE))

Unit.register(None, 5, "molar mass", (UNIT_KILOGRAM,), (UNIT_MOLE,))
Unit.register(None, 5, "concentration", (UNIT_MOLE,), (UNIT_METER, UNIT_METER, UNIT_METER))

def _scientific(num):
    if 0.1 <= abs(num) < 1000000:
        return str(float(num))
    power = 0
    mul = 1
    if abs(num) < 10:
        while abs(num * mul) < 1:
            mul *= 10
            power -= 1
        return str(float(num * mul)) + "\xB710" + _generate_sup_power(power)
    while abs(num / mul) >= 10:
        mul *= 10
        power += 1
    return str(float(num / mul)) + "\xB710" + _generate_sup_power(power)

class Value:
    def __init__(self, number, unit):
        if isinstance(unit, tuple):
            self.number = number * unit[0]
            self.unit = unit[1]
        else:
            self.number = number
            self.unit = unit
    def __repr__(self):
        return _scientific(self.number) + " " + str(self.unit)
    def evaluate(self, context):
        return self
    @staticmethod
    def parse(text):
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

class Variable:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "$" + self.name
    def evaluate(self, context):
        if self.name in context.variables:
            return context.variables[self.name]
        return self
    @staticmethod
    def parse(text):
        return Variable(text.strip()[1:])

CONSTANTS_PHYSICS = {
    "G": Value(6.67428e-11, Unit.parse("N m^2/kg^2")),
    "g_n": Value(9.80665, Unit.parse("m/s^2")),
    "T_0": Value(273.15, Unit.parse("K")),
    "p_0": Value(101325, Unit.parse("Pa")),
    "ε_0": Value(8.854187818e-12, Unit.parse("F/m")),
    "μ_0": Value(8.854187818e-12, Unit.parse("F/m")),
    "k": Value(8.987551787e9, Unit.parse("m/F")),
    "F": Value(96485.338, Unit.parse("C/mol")),
    "c": Value(2.99792458e8, Unit.parse("m/s")),
    "c_0": Value(2.99792458e8, Unit.parse("m/s")),
    "m_e": Value(9.1093822e-31, Unit.parse("kg")),
    "m_p": Value(1.6726216e-27, Unit.parse("kg")),
    "m_n": Value(1.6749273e-27, Unit.parse("kg")),
    "m_d": Value(3.3435835e-27, Unit.parse("kg")),
    "m_α": Value(6.644656e-27, Unit.parse("kg")),
    "h": Value(6.6260693e-34, Unit.parse("J s")),
    "q_e": Value(1.6021766e-19, Unit.parse("C")),
}

CONSTANTS_CHEMISTRY = dict(CONSTANTS_PHYSICS)
CONSTANTS_CHEMISTRY.update({
    "u": Value(1.6605389e-27, Unit.parse("kg")),
    "k": Value(1.3806505e-23, Unit.parse("J/K")),
    "N_A": Value(6.0221415e23, Unit.parse("1/mol")),
    "R": Value(8.314510, Unit.parse("Pa m^3/mol K")),
    "R_H": Value(1.0973731e7, Unit.parse("1/m")),
})

VARS = {
    "phys": CONSTANTS_PHYSICS,
    "chem": CONSTANTS_CHEMISTRY,
}

PARSER = [
    (lambda output: output, re.compile(TOKEN_OUTPUT)),
    (lambda paren: paren, re.compile(TOKEN_PARENTHESIS)),
    (lambda oper: oper, re.compile(TOKEN_OPERATOR)),
    (Variable.parse, re.compile(TOKEN_VARIABLE)),
    (Value.parse, re.compile(TOKEN_VALUE)),
]

def _tokenize_input(text):
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        for kind, regex in PARSER:
            match = regex.match(text, pos)
            if match is not None:
                yield kind(match.group(0))
                pos = match.end()
                break
        else:
            raise MathParseError("invalid syntax at '" + text[:10] + "'")

def _replace_escape(match):
    char = match.group(0)[1]
    try:
        greek_char = GREEK_ALPHABET[LATIN_ALPHABET.index(char)]
        if greek_char == "-":
            raise ValueError
        return greek_char
    except ValueError:
        raise MathParseError("unknown escape \\" + char) from None

def _parse_input(text):
    # normalize µ (U+00B5 MICRO SIGN) to μ (U+03BC GREEK SMALL LETTER MU)
    text = text.replace("\xB5", "\u03BC")
    # parse escapes
    text = ESCAPE_REGEX.sub(_replace_escape, text)
    tokens = _tokenize_input(text)
    for token in tokens:
        first = token
        # TODO: print(token)
    return first

class Context:
    def __init__(self):
        self.outputs = []
        self.variables = {
            "e": Value(math.e, Unit.parse("")),
            "pi": Value(math.pi, Unit.parse("")),
            "π": Value(math.pi, Unit.parse("")),
        }

HELP_SYNTAX = APPLICATION + """ parses input as operators and values.

Values can be constants, expressed as a number followed by an optional unit.
Numbers can be integers, integer ratios or decimal numbers.
All SI units and prefixes except for becquerel, gray, sievert and katal are supported.

Values can also be variables, expressed as $name, or previous results, expressed as [num].

The following operators are supported: + - * / ^

See also: !help greek"""
HELP_GREEK = """Greek characters can be typed as \\x, where x is from the following table:

a b c d e f g h i j k l m n o p q r s t u v w x y z
α β γ δ ε φ γ χ ι η κ λ μ ν ω π ψ ρ σ τ υ θ   ξ   ζ

A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
Α Β Γ Δ Ε Φ Γ Χ Ι Η Κ Λ Μ Ν Ω Π Ψ Ρ Σ Τ Υ Θ   Ξ   Ζ

Most characters translate to their Greek counterparts. Exceptions:
 - \\c = γ (gamma, \\g also works)
 - \\j = η (eta)
 - \\q = ψ (psi)
 - \\v = θ (theta)"""
HELP_LOAD = """Usage: !load <vars>
Load variables to the context.
<vars> can be one of """ + ", ".join(sorted(VARS))
HELP_VARS = """Usage: !vars
List variables in the context."""
HELPS = {
    "syntax": HELP_SYNTAX,
    "greek": HELP_GREEK,
    "load": HELP_LOAD,
    "vars": HELP_VARS
}
HELP_GLOBAL = """Type expressions to compute them.
Type !help <topic> to get help on a specific topic.
Topics: """ + ", ".join(sorted(HELPS))

def _run_command(context, command, *args):
    if command == "!help":
        if args and args[0] in HELPS:
            print(HELPS[args[0]])
        else:
            print(HELP_GLOBAL)
    elif command == "!load":
        if len(args) != 1 or args[0] not in VARS:
            print("Usage: !load <vars>\nType !help load for help.")
        else:
            context.variables.update(VARS[args[0]])
    elif command == "!vars":
        for var in sorted(context.variables):
            print("$" + var + " = " + str(context.variables[var]))
    else:
        print("Unknown command " + command + ". Type !help for help.")

def _main():
    print(LAUNCH_CREDITS)
    context = Context()
    # setup readline if on posix
    if os.name == "posix":
        try:
            import readline
            # load history file if any exists
            history_file = os.path.join(os.path.expanduser("~"), ".physcalc_history")
            try:
                readline.read_history_file(history_file)
            except FileNotFoundError:
                pass
            readline.set_history_length(1000)
            # save history file on exit
            atexit.register(readline.write_history_file, history_file)
        except ImportError:
            pass
    while True:
        prompt = " " * len(str(len(context.outputs))) + " > "
        try:
            line = input(prompt).strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line[0] == "!":
            _run_command(context, *line.split(None))
        else:
            try:
                code = _parse_input(line)
                result = code.evaluate(context)
                context.outputs.append(result)
                if isinstance(result, Value) and result.unit.variable is not None:
                    print("[" + str(len(context.outputs)) + "] " + str(result) + " (" + result.unit.variable + ")")
                else:
                    print("[" + str(len(context.outputs)) + "] " + str(result))
            except MathParseError as ex:
                print("Syntax error: " + ex.args[0])
            except MathEvalError as ex:
                print("Evaluation error: " + ex.args[0])

if __name__ == "__main__":
    _main()
