FEATURE_DEBUG = "debug"
FEATURE_FRAC = "frac"
FEATURE_GRAPHIC = "graphic"
FEATURE_CONT = "cont"

class Context:
    def __init__(self):
        from constants import CONSTANTS_MATH
        self.outputs = []
        self.variables = dict(CONSTANTS_MATH)
        self.features = {
            FEATURE_DEBUG: False,
            FEATURE_FRAC: False,
            FEATURE_GRAPHIC: False,
            FEATURE_CONT: True,
        }
