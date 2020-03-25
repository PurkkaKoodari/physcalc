import re

from physcalc.context import FEATURE_CONT
from physcalc.syntax import ESCAPE_REGEX, TOKEN_OUTPUT, TOKEN_OPERATOR, TOKEN_VARIABLE, TOKEN_VALUE, TOKEN_SPECIAL, Token
from physcalc.util import MathParseError, debug
from physcalc.value import Output, Operator, Variable, Value, Expression, PowerExpression, UnaryMinus
from physcalc.value import PREC_ADD, PREC_MULTIPLY, PREC_POWER

MAX_UNIT_WEIGHT = 5

LATIN_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
GREEK_ALPHABET = "αβγδεφγχιηκλμνωπψρστυθ-ξ-ζΑΒΓΔΕΦΓΧΙΗΚΛΜΝΩΠΨΡΣΤΥΘ-Ξ-Ζ"

class SpecialToken(Token):
    def __init__(self, name):
        self.name = name
    def token_name(self):
        return self.name

EQUALS = SpecialToken("equals")
ASSIGNMENT = SpecialToken("assignment")
LEFT_PAREN = SpecialToken("left paren")
RIGHT_PAREN = SpecialToken("right paren")

SPECIAL_TOKENS = {
    "=": EQUALS,
    ":=": ASSIGNMENT,
    "(": LEFT_PAREN,
    ")": RIGHT_PAREN,
}

PARSER = [
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
    while pos + 1 < len(tokens) and tokens[pos + 1] is ASSIGNMENT:
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
                return UnaryMinus(parse_primary())
            elif pos == start:
                if not context.features[FEATURE_CONT] or not context.outputs:
                    raise MathParseError("missing value before " + tokens[pos].token_name())
                else:
                    return context.outputs[-1]
            else:
                raise MathParseError("found " + tokens[pos].token_name() + " when expecting a value")
        elif isinstance(tokens[pos], SpecialToken):
            if tokens[pos] is LEFT_PAREN:
                pos += 1
                return parse_recursive(PREC_ADD, True, True)
            else:
                raise MathParseError("found " + tokens[pos].token_name() + " when expecting a value")
        else:
            pos += 1
            return tokens[pos - 1]
    def parse_recursive(prec, allow_paren, consume_paren):
        nonlocal pos
        if prec > PREC_POWER:
            return parse_primary()
        subexprs = [parse_recursive(prec + 1, allow_paren, False)]
        operators = []
        while pos < len(tokens):
            if tokens[pos] is RIGHT_PAREN:
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
            else:
                raise MathParseError("found " + tokens[pos].token_name() + " when expecting an operator")
        if len(subexprs) == 1:
            return subexprs[0]
        if operators[0].prec == PREC_POWER:
            return PowerExpression(subexprs)
        return Expression(subexprs, operators)
    return assignments, parse_recursive(PREC_ADD, False, False)
