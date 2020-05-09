import re
from abc import ABC, abstractmethod

ESCAPE_REGEX = re.compile(r"\\.")

PART_POSITIVE_DECIMAL = r"(?:\d+(?:\.\d*)?|\.\d+)"
PART_DECIMAL = r"-?" + PART_POSITIVE_DECIMAL
PART_POSITIVE_FRACTION = r"\d+(?:/\d+)?"
PART_FRACTION = r"-?" + PART_POSITIVE_FRACTION
PART_POSITIVE_NUMBER = r"\d+(?:/\d+|\.\d*)?|\.\d+"
PART_NUMBER = r"-?(?:" + PART_POSITIVE_NUMBER + r")"

PART_VARIABLE_NAME = r"[A-Za-z\u0370-\u03FF]+"
PART_SUBSCRIPT_CONTENT = r"[A-Za-z0-9\u0370-\u03FF]+"

PART_POWER = r"\^" + PART_DECIMAL + r"|\u207B?[\xB2\xB3\xB9\u2070\u2074-\u2079]+"
PART_SUBSCRIPT = r"_" + PART_SUBSCRIPT_CONTENT

PART_UNIT_POWER = PART_VARIABLE_NAME + r"(?:" + PART_POWER + r")?"
PART_UNIT_POWERS = PART_UNIT_POWER + r"(?:\s+" + PART_UNIT_POWER + r")*"
PART_UNIT = r"(?:" + PART_UNIT_POWERS + r")+(?:\s*/\s*(?:" + PART_UNIT_POWERS + r")+)?"

TOKEN_OUTPUT = r"\[\d+\]"
TOKEN_VARIABLE = PART_VARIABLE_NAME + r"(?:" + PART_SUBSCRIPT + r")?"
TOKEN_FUNCTION = TOKEN_VARIABLE + r"\("
TOKEN_VALUE = r"(?:" + PART_POSITIVE_NUMBER + r")(?:\s*" + PART_UNIT + r")?"
TOKEN_OPERATOR = r"\*\*|[+\-*\xB7\xD7/\xF7^]"
TOKEN_SPECIAL = r":?=|[(),]"


class Token(ABC):
    @abstractmethod
    def token_name(self):
        pass
