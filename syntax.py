import re
from abc import ABC, abstractmethod

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
TOKEN_VARIABLE = SUBTOKEN_VARIABLE_NAME + r"(?:" + SUBTOKEN_SUBSCRIPT + r")?"
TOKEN_VALUE = r"(?:" + SUBTOKEN_POSITIVE_NUMBER + r")(?:" + SUBTOKEN_UNIT + r")?"
TOKEN_OPERATOR = r"\*\*|[+\-*\xB7\xD7/\xF7^]"
TOKEN_SPECIAL = r":?=|[()]"

class Token(ABC):
    @abstractmethod
    def token_name(self):
        pass
