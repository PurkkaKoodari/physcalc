def iterlen(itr):
    return sum(1 for _ in itr)

SUP_CHARS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁻"
DECIMAL_TO_SUP = dict(zip(map(ord, "0123456789-"), SUP_CHARS))
SUP_TO_DECIMAL = dict(zip(map(ord, SUP_CHARS), "0123456789-"))

def generate_sup_power(power):
    return str(power).translate(DECIMAL_TO_SUP) if power != 1 else ""

def parse_power(text):
    if "^" in text:
        return text.split("^", 1)
    if text[-1] in SUP_CHARS:
        unit = text.rstrip(SUP_CHARS)
        return unit, text[len(unit):].translate(SUP_TO_DECIMAL)
    return text, 1

class MathParseError(Exception):
    pass

class MathEvalError(Exception):
    pass

def scientific(num):
    if 0.1 <= abs(num) < 1000000:
        return str(float(num))
    power = 0
    mul = 1
    if abs(num) < 10:
        while abs(num * mul) < 1:
            mul *= 10
            power -= 1
        return str(float(num * mul)) + "\xB710" + generate_sup_power(power)
    while abs(num / mul) >= 10:
        mul *= 10
        power += 1
    return str(float(num / mul)) + "\xB710" + generate_sup_power(power)

class debug:
    recur = 0
    def __init__(self, func):
        self.func = func
    def __call__(self, *args, **kwargs):
        argstr = [self.func.__name__]
        argstr.extend(repr(arg) for arg in args)
        argstr.extend(key + "=" + repr(val) for key, val in kwargs.values())
        print(" " * debug.recur + ">" + " ".join(argstr))
        debug.recur += 1
        ret = self.func(*args, **kwargs)
        debug.recur -= 1
        print(" " * debug.recur + "<" + self.func.__name__ + " " + repr(ret))
        return ret
