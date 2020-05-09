from enum import Enum


class Feature(Enum):
    DEBUG = "debug"
    FRAC = "frac"
    GRAPHIC = "graphic"
    CONT = "cont"


class Context:
    def __init__(self):
        from physcalc.constants import CONSTANTS_MATH
        self.outputs = []
        self.variables = dict(CONSTANTS_MATH)
        self.features = {
            Feature.DEBUG: False,
            Feature.FRAC: False,
            Feature.GRAPHIC: False,
            Feature.CONT: True,
        }
