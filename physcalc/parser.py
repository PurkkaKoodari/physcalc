import re

from physcalc.context import Feature
from physcalc.operator import Operator
from physcalc.syntax import (ESCAPE_REGEX, TOKEN_OUTPUT, TOKEN_OPERATOR, TOKEN_VARIABLE, TOKEN_VALUE, TOKEN_SPECIAL,
                             Token, TOKEN_CAST)
from physcalc.unit import Unit
from physcalc.util import MathParseError
from physcalc.value import Output, Variable, Value, OperatorExpression, PowerExpression, UnaryMinus, OpPrecedence


class SpecialToken(Token):
    name: str
    
    def __init__(self, name):
        self.name = name

    def token_name(self):
        return self.name
    

SpecialToken.EQUALS = SpecialToken("equals")
SpecialToken.ASSIGNMENT = SpecialToken("assignment")
SpecialToken.LEFT_PAREN = SpecialToken("left paren")
SpecialToken.RIGHT_PAREN = SpecialToken("right paren")
SpecialToken.COMMA = SpecialToken("comma")


class UnitCast(Token):
    unit: Unit

    def __init__(self, unit):
        self.unit = unit

    def token_name(self):
        return f"conversion to {self.unit.name}"

    @staticmethod
    def parse(text, _):
        unit = Unit.parse(text[3:].strip())
        return UnitCast(unit)


MAX_UNIT_WEIGHT = 5

LATIN_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
GREEK_ALPHABET = "αβγδεφγχιηκλμνωπψρστυθ-ξ-ζΑΒΓΔΕΦΓΧΙΗΚΛΜΝΩΠΨΡΣΤΥΘ-Ξ-Ζ"

SPECIAL_TOKENS = {
    "=": SpecialToken.EQUALS,
    ":=": SpecialToken.ASSIGNMENT,
    "(": SpecialToken.LEFT_PAREN,
    ")": SpecialToken.RIGHT_PAREN,
    ",": SpecialToken.COMMA,
}

PARSER = [
    (UnitCast.parse, re.compile(TOKEN_CAST)),
    (Output.parse, re.compile(TOKEN_OUTPUT)),
    (Operator.parse, re.compile(TOKEN_OPERATOR)),
    (Variable.parse, re.compile(TOKEN_VARIABLE)),
    (Value.parse, re.compile(TOKEN_VALUE)),
    (SPECIAL_TOKENS.get, re.compile(TOKEN_SPECIAL)),
]


def _tokenize_input(text, context):
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        for prec, regex in PARSER:
            match = regex.match(text, pos)
            if match is not None:
                yield prec(match.group(0), context)
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


def parse_input(text, context):
    # normalize µ (U+00B5 MICRO SIGN) to μ (U+03BC GREEK SMALL LETTER MU)
    text = text.replace("\xB5", "\u03BC")
    # parse escapes
    text = ESCAPE_REGEX.sub(_replace_escape, text)
    tokens = list(_tokenize_input(text, context))
    pos = 0
    assignments = []
    while pos + 1 < len(tokens) and tokens[pos + 1] is SpecialToken.ASSIGNMENT:
        if not isinstance(tokens[pos], Variable):
            raise MathParseError("cannot assign to " + tokens[pos].token_name())
        assignments.append(tokens[pos])
        pos += 2
    start = pos

    def parse_primary():
        nonlocal pos
        if pos >= len(tokens):
            raise MathParseError("missing value at end of line")
        if isinstance(tokens[pos], Operator):
            if tokens[pos].is_unary:
                pos += 1
                return UnaryMinus.create(parse_primary())
            elif pos == start:
                if not context.features[Feature.CONT] or not context.outputs:
                    raise MathParseError("missing value before " + tokens[pos].token_name())
                else:
                    return context.outputs[-1]
            else:
                raise MathParseError("found " + tokens[pos].token_name() + " when expecting a value")
        elif isinstance(tokens[pos], SpecialToken):
            if tokens[pos] is SpecialToken.LEFT_PAREN:
                pos += 1
                return parse_recursive(OpPrecedence.ADD, True, True)
            else:
                raise MathParseError("found " + tokens[pos].token_name() + " when expecting a value")
        elif isinstance(tokens[pos], UnitCast):
            raise MathParseError("found " + tokens[pos].token_name() + " when expecting a value")
        else:
            pos += 1
            return tokens[pos - 1]

    def parse_recursive(prec, allow_paren, consume_paren):
        nonlocal pos
        if prec > OpPrecedence.POWER:
            return parse_primary()
        subexprs = [parse_recursive(prec + 1, allow_paren, False)]
        operators = []
        while pos < len(tokens):
            if tokens[pos] is SpecialToken.RIGHT_PAREN:
                if not allow_paren:
                    raise MathParseError("unmatched parenthesis")
                if consume_paren:
                    pos += 1
                break
            elif isinstance(tokens[pos], Operator):
                if tokens[pos].prec < prec:
                    break
                assert tokens[pos].prec == prec
                operators.append(tokens[pos])
                pos += 1
                subexprs.append(parse_recursive(prec + 1, allow_paren, False))
            elif isinstance(tokens[pos], UnitCast):
                break
            else:
                raise MathParseError("found " + tokens[pos].token_name() + " when expecting an operator")
        if len(subexprs) == 1:
            return subexprs[0]
        if operators[0].prec == OpPrecedence.POWER:
            return PowerExpression(subexprs)
        return OperatorExpression(subexprs, operators)

    expression = parse_recursive(OpPrecedence.ADD, False, False)
    cast = None

    if pos < len(tokens):
        if not isinstance(tokens[pos], UnitCast):
            raise MathParseError("found " + tokens[pos].token_name() + " when expecting end of input")
        if pos != len(tokens) - 1:
            raise MathParseError("found " + tokens[pos + 1].token_name() + " after " + tokens[pos].token_name())
        cast = tokens[pos].unit

    return assignments, expression, cast
