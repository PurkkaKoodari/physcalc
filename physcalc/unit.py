import math
import re
from collections import Counter, OrderedDict, defaultdict
from enum import IntEnum
from fractions import Fraction
from itertools import groupby, combinations, permutations
from numbers import Real
from typing import FrozenSet
from typing import Iterable, Tuple, List, Dict, TypeVar, Optional, Set, Mapping, DefaultDict

from physcalc.util import (MathParseError, MathEvalError, parse_power, generate_sup_power, iterlen, ensure_real,
                           ensure_int)

T = TypeVar("T")


class BaseUnit(IntEnum):
    AMPERE = 1
    KILOGRAM = 2
    METER = 3
    SECOND = 4
    KELVIN = 5
    MOLE = 6
    CANDELA = 7


BASE_UNIT_NAMES = {
    BaseUnit.METER: "m",
    BaseUnit.KILOGRAM: "kg",
    BaseUnit.SECOND: "s",
    BaseUnit.KELVIN: "K",
    BaseUnit.AMPERE: "A",
    BaseUnit.MOLE: "mol",
    BaseUnit.CANDELA: "cd",
}

MUL_PREFIXES = OrderedDict((
    ("", Fraction(1, 1)),
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
    ("μ", Fraction(1, 1000) ** 2),
    ("u", Fraction(1, 1000) ** 2),
    ("n", Fraction(1, 1000) ** 3),
    ("p", Fraction(1, 1000) ** 4),
    ("f", Fraction(1, 1000) ** 5),
    ("a", Fraction(1, 1000) ** 6),
    ("z", Fraction(1, 1000) ** 7),
    ("y", Fraction(1, 1000) ** 8),
))

# by default, non-multiplicative units won't be prefixed with the non-1000^n prefixes
DEFAULT_DISALLOWED_PREFIXES = frozenset(("c", "d", "da", "h"))
# by default, multiplicative and anonymous units won't be prefixed at all
ALL_DISALLOWED_PREFIXES = frozenset(MUL_PREFIXES.keys()) - frozenset(("",))

DISALLOWED_PREFIXES: "DefaultDict[Unit, FrozenSet[str]]" = defaultdict(lambda: ALL_DISALLOWED_PREFIXES)
PREFIX_POWER: "DefaultDict[Unit, int]" = defaultdict(lambda: 1)

WHITESPACE_RE = re.compile(r"\s+")


def _parse_multiplied_unit(unit_name: str) -> "Unit":
    """Parses a unit name with optional multiplier."""
    for prefix, prefix_mul in MUL_PREFIXES.items():
        for name, unit in Unit.name_registry.items():
            if unit_name == prefix + name:
                return unit * prefix_mul
    raise MathParseError(f"unknown unit {unit_name}")


def _parse_unit_half(text) -> "Tuple[Unit, Mapping[str, int]]":
    """Parses unit names separated by whitespace into a single unit and a name list."""
    total_unit = NO_UNIT
    total_names = Counter()
    parts = WHITESPACE_RE.split(text)
    if parts == ["1"]:
        return total_unit, total_names
    for part in parts:
        if not part:
            continue
        unit_name, power = parse_power(part)
        unit = _parse_multiplied_unit(unit_name)
        try:
            power = int(power)
        except ValueError:
            raise MathParseError(f"invalid power {power}") from None
        for _ in range(power):
            total_unit *= unit
            total_names[unit_name] += 1
        for _ in range(-power):
            total_unit /= unit
            total_names[unit_name] -= 1
    return total_unit, total_names


def _cancel_unit_parts(num: Iterable[T], denom: Iterable[T]) -> Tuple[Tuple[T, ...], Tuple[T, ...]]:
    """Simplifies a numerator-denumerator pair."""
    counts = Counter(num)
    counts.subtract(denom)
    num_list = []
    denom_list = []
    for item, count in sorted(counts.items()):
        for _ in range(count):
            num_list.append(item)
        for _ in range(-count):
            denom_list.append(item)
    return tuple(num_list), tuple(denom_list)


def _generate_base_name_half(part: Iterable[str]) -> Tuple[str, int]:
    """Generates a unit name with powers from a sorted list of unit names."""
    if not part:
        return "", 1
    units = []
    weight = 1
    for unit, power in groupby(part):
        units.append(unit + generate_sup_power(iterlen(power)))
        weight *= 2
    return " ".join(units), weight


def _multiply_list_by_frac(lst, frac):
    """Multiplies a list of base units by a fraction, ensuring that no fractional powers result."""
    out = []
    if len(lst) % frac.denominator:
        raise ValueError(f"number of base units in unit not divisible by {frac.denominator}")
    for i in range(0, len(lst), frac.denominator):
        if any(lst[i] != lst[i + j] for j in range(frac.denominator)):
            raise ValueError(f"number of {BASE_UNIT_NAMES[lst[i]]} in unit not divisible by {frac.denominator}")
        for _ in range(frac.numerator):
            out.append(lst[i])
    return out


class Unit:
    part_registry: "Dict[tuple, Unit]" = {}
    name_registry: "Dict[str, Unit]" = {}
    output_units: "Set[Unit]" = set()
    named_units: "List[Unit]" = []

    specific_name: bool
    _name: Optional[str]
    output_weight: int
    quantity_name: Optional[str]
    multiplier: Real

    def __init__(self, specific_name: Optional[str], num, denom, output_weight: int = 1000, quantity_name: Optional[str] = None, multiplier: Real = 1):
        self.specific_name = specific_name is not None
        self._name = specific_name
        self._num = num
        self._denom = denom
        self.output_weight = output_weight
        self.quantity_name = quantity_name
        self.multiplier = multiplier

    def _register_key(self):
        key = (self._num, self._denom, self.multiplier)
        if key in Unit.part_registry:
            raise ValueError("unit already registered")
        Unit.part_registry[key] = self

    def _register_name(self, derivative):
        if self.name in Unit.name_registry:
            raise ValueError(f"unit with name {self.name} already registered")
        Unit.named_units.append(self)
        if not derivative:
            Unit.output_units.add(self)
        Unit.name_registry[self.name] = self

    def register_derivative(self, specific_name: str, multiplier: Real, disallowed_prefixes=None):
        """Creates a new derivative Unit of this Unit."""
        deriv = Unit(specific_name, self._num, self._denom, 1000, self.quantity_name, self.multiplier * multiplier)
        deriv._register_name(True)
        if disallowed_prefixes is not None:
            DISALLOWED_PREFIXES[deriv] = disallowed_prefixes
        return deriv

    @staticmethod
    def register(specific_name: Optional[str], output_weight: int, quantity_name: str, num, denom=(), disallowed_prefixes=None, prefix_power=None):
        """Creates a new Unit with the given properties."""
        num, denom = _cancel_unit_parts(num, denom)
        created = Unit(specific_name, num, denom, output_weight, quantity_name)
        created._register_key()
        if specific_name is not None:
            created._register_name(False)
        if specific_name is not None or disallowed_prefixes is not None:
            DISALLOWED_PREFIXES[created] = DEFAULT_DISALLOWED_PREFIXES if disallowed_prefixes is None else frozenset(disallowed_prefixes)
        if prefix_power is not None:
            PREFIX_POWER[created] = prefix_power
        return created

    @staticmethod
    def from_parts(num, denom, multiplier):
        """Gets a Unit from the given numerator, denominator and multiplier.

        If the combination is already known, returns the previously created Unit. Otherwise, an anonymous unit is
        created and registered for this combination.
        """
        num, denom = _cancel_unit_parts(num, denom)
        key = (num, denom, multiplier)
        try:
            return Unit.part_registry[key]
        except KeyError:
            unit = Unit(None, num, denom, multiplier=multiplier)
            unit._register_key()
            return unit

    @staticmethod
    def parse(name):
        """Parses a unit specification.

        The resulting unit will keep the given name and may be multiplied. To convert it to a non-multiplied unit,
        use to_si().
        """
        num, denom = name.split("/") if "/" in name else (name, "")
        num, num_names = _parse_unit_half(num)
        denom, denom_names = _parse_unit_half(denom)
        num_names, denom_names = _cancel_unit_parts(num_names, denom_names)
        name = _generate_base_name_half(num_names)[0]
        if denom_names:
            name += " / " + _generate_base_name_half(denom_names)[0]
        unit = num / denom
        return Unit(name, unit._num, unit._denom, 1000, unit.quantity_name, unit.multiplier)

    @property
    def name(self):
        if self._name is None:
            self._name = self._generate_name()
        return self._name

    def _generate_name(self):
        """Generates potential names for a unit."""
        if not self._num and not self._denom:
            return ""
        # generate name derived from the base units that make up this unit
        basic_name, basic_weight = _generate_base_name_half(BASE_UNIT_NAMES[unit] for unit in self._num)
        if self._denom:
            basic_denom, denom_weight = _generate_base_name_half(BASE_UNIT_NAMES[unit] for unit in self._denom)
            basic_name += " / " + basic_denom
            basic_weight *= denom_weight
        results: List[Tuple[str, int]] = [(basic_name, basic_weight)]
        # generate all reasonable powers of known units
        for test in Unit.output_units:
            max_power = min(len(self._num), len(self._denom))
            for power in range(-max_power, max_power + 1):
                if 0 <= power <= 1:
                    continue
                if self.can_convert(test ** power):
                    results.append((test.name + generate_sup_power(power), test.output_weight * 2))
        # generate all products of two known units
        for first, second in combinations(Unit.output_units, 2):
            if self.can_convert(first * second):
                results.append((f"{first.name} {second.name}", first.output_weight * second.output_weight))
        # generate all quotients of two known units
        for num, denom in permutations(Unit.output_units, 2):
            if self.can_convert(num / denom):
                results.append((f"{num.name} / {denom.name}", num.output_weight * denom.output_weight))
        # pick the name with the minimum weight
        return min(results, key=lambda pair: pair[1])[0]

    def can_convert(self, other: "Unit"):
        return self._num == other._num and self._denom == other._denom

    def __mul__(self, other):
        if isinstance(other, Real):
            return Unit.from_parts(self._num, self._denom, self.multiplier * other)
        if not isinstance(other, Unit):
            return NotImplemented
        return Unit.from_parts(self._num + other._num, self._denom + other._denom, self.multiplier * other.multiplier)

    def __truediv__(self, other):
        if not isinstance(other, Unit):
            return NotImplemented
        return Unit.from_parts(self._num + other._denom, self._denom + other._num, self.multiplier / other.multiplier)

    def __rtruediv__(self, other):
        if other == 1:
            return NO_UNIT / self
        return NotImplemented

    def __pow__(self, power):
        # special case for 0
        if power == 0 or self is NO_UNIT:
            return NO_UNIT

        # only real powers allowed for non-empty units
        try:
            power = ensure_real(power)
        except ValueError:
            raise MathEvalError(f"cannot raise {self} to complex power {power}") from None

        if isinstance(power, Fraction):
            # fractional powers
            try:
                num = _multiply_list_by_frac(self._num, abs(power))
                denom = _multiply_list_by_frac(self._denom, abs(power))
            except ValueError:
                raise MathEvalError(f"cannot raise {self} to power {power}") from None
        else:
            # integral powers
            try:
                power = ensure_int(power)
            except ValueError:
                raise MathEvalError(f"cannot raise {self} to non-rational power {power}") from None
            num = self._num * abs(power)
            denom = self._denom * abs(power)

        # negative powers
        if power < 0:
            num, denom = denom, num

        return Unit.from_parts(num, denom, self.multiplier ** power)

    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, Unit):
            return False
        return self.name == other.name and self._num == other._num and self._denom == other._denom and self.multiplier == other.multiplier

    def __hash__(self):
        return hash((self._name if self.specific_name else None, self._num, self._denom, self.multiplier))

    def __str__(self):
        return self.name or "1"

    def __repr__(self):
        return f"<unit {self.name or '1'}>"

    def to_si(self):
        """Converts this Unit to a multiplier and non-multiplied unit."""
        if self in Unit.output_units:
            return 1, self
        return self.multiplier, Unit.from_parts(self._num, self._denom, 1)


NO_UNIT = Unit.register(None, 2, "number", (), (), ALL_DISALLOWED_PREFIXES)

# SI base units
AMPERE = Unit.register("A", 2, "electric current", (BaseUnit.AMPERE,))
KILOGRAM = Unit.register("kg", 2, "mass", (BaseUnit.KILOGRAM,))
METER = Unit.register("m", 2, "distance", (BaseUnit.METER,))
SECOND = Unit.register("s", 2, "time", (BaseUnit.SECOND,))
KELVIN = Unit.register("K", 2, "temperature", (BaseUnit.KELVIN,))
MOLE = Unit.register("mol", 2, "amount of substance", (BaseUnit.MOLE,))
CANDELA = Unit.register("cd", 2, "luminous intensity", (BaseUnit.CANDELA,))

# SI derived units
NEWTON = Unit.register("N", 3, "force", (BaseUnit.KILOGRAM, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND))
JOULE = Unit.register("J", 3, "energy", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND))
PASCAL = Unit.register("Pa", 4, "pressure", (BaseUnit.KILOGRAM,), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.METER), ("c", "d", "da"))
WATT = Unit.register("W", 4, "power", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND))

COULOMB = Unit.register("C", 3, "electric charge", (BaseUnit.AMPERE, BaseUnit.SECOND))
VOLT = Unit.register("V", 3, "voltage", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE))
FARAD = Unit.register("F", 4, "capacitance", (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE), (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER))
OHM = Unit.register("\u03A9", 4, "resistance", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE))
SIEMENS = Unit.register("S", 5, "conductance", (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE), (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER))
WEBER = Unit.register("Wb", 4, "magnetic flux", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE))
TESLA = Unit.register("T", 4, "magnetic flux density", (BaseUnit.KILOGRAM,), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE))
HENRY = Unit.register("H", 4, "inductance", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE))

HERTZ = Unit.register("Hz", 4, "frequency", (), (BaseUnit.SECOND,))

LUX = Unit.register("lux", 3, "illuminance", (BaseUnit.CANDELA,), (BaseUnit.METER, BaseUnit.METER))
LUMEN = CANDELA.register_derivative("lm", 1)

GRAY = Unit.register("Gy", 5, "radiation dose", (BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND))
KATAL = Unit.register("kat", 5, "katalytic activity", (BaseUnit.MOLE,), (BaseUnit.SECOND,), ALL_DISALLOWED_PREFIXES)

BECQUEREL = HERTZ.register_derivative("Bq", 1, DEFAULT_DISALLOWED_PREFIXES)
SIEVERT = GRAY.register_derivative("Sv", 1, DEFAULT_DISALLOWED_PREFIXES)

# Named quantities without named SI units
AREA = Unit.register(None, 3, "area", (BaseUnit.METER, BaseUnit.METER), (), ("d", "da", "h"), 2)
VOLUME = Unit.register(None, 4, "volume", (BaseUnit.METER, BaseUnit.METER, BaseUnit.METER), (), ("da", "h"), 3)
SPEED = Unit.register(None, 3, "speed", (BaseUnit.METER,), (BaseUnit.SECOND,))
ACCELERATION = Unit.register(None, 4, "acceleration", (BaseUnit.METER,), (BaseUnit.SECOND, BaseUnit.SECOND))
MOMENTUM = Unit.register(None, 4, "momentum", (BaseUnit.KILOGRAM, BaseUnit.METER), (BaseUnit.SECOND,))

ANGULAR_MOMENTUM = Unit.register(None, 5, "angular momentum", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND,))
MOMENT_OF_INERTIA = Unit.register(None, 5, "moment of inertia", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), ())

ELECTRIC_FIELD = Unit.register(None, 4, "electric field strength", (BaseUnit.KILOGRAM, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE))
MAGNETIC_FIELD = Unit.register(None, 4, "magnetic field strength", (BaseUnit.AMPERE,), (BaseUnit.METER,))
CHARGE_DENSITY = Unit.register(None, 5, "electric charge density", (BaseUnit.AMPERE, BaseUnit.SECOND), (BaseUnit.METER, BaseUnit.METER, BaseUnit.METER))
RESISTIVITY = Unit.register(None, 5, "resistivity", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE))
CONDUCTIVITY = Unit.register(None, 5, "conductivity", (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE), (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER, BaseUnit.METER))
PERMITTIVITY = Unit.register(None, 5, "permittivity", (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE), (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER, BaseUnit.METER))
PERMEABILITY = Unit.register(None, 5, "magnetic permeability", (BaseUnit.KILOGRAM, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.AMPERE, BaseUnit.AMPERE))

THERMAL_CONDUCTIVITY = Unit.register(None, 5, "thermal conductivity", (BaseUnit.KILOGRAM, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.KELVIN))
THERMAL_CAPACITY = Unit.register(None, 5, "thermal capacity", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.KELVIN))
SPECIFIC_THERMAL_CAPACITY = Unit.register(None, 5, "specific thermal capacity", (BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.KELVIN))

MOLAR_THERMAL_CAPACITY = Unit.register(None, 5, "molar thermal capacity", (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER), (BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.KELVIN, BaseUnit.MOLE))
MOLAR_MASS = Unit.register(None, 5, "molar mass", (BaseUnit.KILOGRAM,), (BaseUnit.MOLE,))
CONCENTRATION = Unit.register(None, 5, "concentration", (BaseUnit.MOLE,), (BaseUnit.METER, BaseUnit.METER, BaseUnit.METER))

LUMINOUS_ENERGY = Unit.register(None, 5, "luminous energy", (BaseUnit.CANDELA, BaseUnit.SECOND))
LUMINOUS_EXPOSURE = Unit.register(None, 5, "luminous exposure", (BaseUnit.CANDELA, BaseUnit.SECOND), (BaseUnit.METER, BaseUnit.METER))
LUMINOUS_EFFICACY = Unit.register(None, 5, "luminous efficacy", (BaseUnit.CANDELA, BaseUnit.SECOND, BaseUnit.SECOND, BaseUnit.SECOND), (BaseUnit.KILOGRAM, BaseUnit.METER, BaseUnit.METER))

RADIOACTIVE_EXPOSURE = Unit.register(None, 5, "radioactive exposure", (BaseUnit.AMPERE, BaseUnit.SECOND), (BaseUnit.KILOGRAM,))

# Multiplied SI units
ANGSTROM = METER.register_derivative("Å", Fraction(1, 10 ** 10))
GRAM = KILOGRAM.register_derivative("g", Fraction(1, 1000), DEFAULT_DISALLOWED_PREFIXES)
ERG = JOULE.register_derivative("erg", Fraction(1, 10 ** 7))
LITER = VOLUME.register_derivative("l", Fraction(1, 1000), ("da", "h"))
HECTARE = AREA.register_derivative("ha", 10000)

BAR = PASCAL.register_derivative("bar", 100000, DEFAULT_DISALLOWED_PREFIXES)
ATM = PASCAL.register_derivative("atm", 101325)
MM_MERCURY = PASCAL.register_derivative("mmHg", 133.322387415)
INCH_MERCURY = PASCAL.register_derivative("inHg", 3386.389)
TORR = PASCAL.register_derivative("Torr", Fraction(101325, 760))

MINUTE = SECOND.register_derivative("min", 60)
HOUR = MINUTE.register_derivative("h", 60)
DAY = HOUR.register_derivative("d", 24)

ASTRONOMICAL_UNIT = METER.register_derivative("AU", 149597870700)
KILOMETER_PER_HOUR = SPEED.register_derivative("kph", 1000 / HOUR.multiplier)

DEGREE = NO_UNIT.register_derivative("deg", math.pi / 180)
ARC_MINUTE = DEGREE.register_derivative("'", 1 / 60)
ARC_SECOND = ARC_MINUTE.register_derivative("\"", 1 / 60)

CALORIE = JOULE.register_derivative("cal", 4.184, DEFAULT_DISALLOWED_PREFIXES)
ELECTRON_VOLT = JOULE.register_derivative("eV", 1.602176634e-19, DEFAULT_DISALLOWED_PREFIXES)

CURIE = BECQUEREL.register_derivative("Ci", 3.7e10, DEFAULT_DISALLOWED_PREFIXES)
RAD = GRAY.register_derivative("rad", Fraction(1, 10000), DEFAULT_DISALLOWED_PREFIXES)
ROENTGEN = RADIOACTIVE_EXPOSURE.register_derivative("R", 2.58e-4, DEFAULT_DISALLOWED_PREFIXES)

# US customary units
INCH = METER.register_derivative("in", 0.0254)
FOOT = INCH.register_derivative("ft", 12)
YARD = FOOT.register_derivative("yd", 3)
MILE = YARD.register_derivative("mi", 1760)
NAUTICAL_MILE = METER.register_derivative("NM", 1852)

MILE_PER_HOUR = SPEED.register_derivative("mph", MILE.multiplier / HOUR.multiplier)

ACRE = AREA.register_derivative("ac", 43560 * FOOT.multiplier ** 2)

POUND = KILOGRAM.register_derivative("lb", 0.45359237)
POUND_FORCE = NEWTON.register_derivative("lbf", POUND.multiplier * 9.80665)
FOOT_POUND = JOULE.register_derivative("ftlb", POUND_FORCE.multiplier * FOOT.multiplier)
PSI = PASCAL.register_derivative("psi", POUND_FORCE.multiplier / INCH.multiplier ** 2)

US_GALLON = VOLUME.register_derivative("gal", 231 * INCH.multiplier ** 3)
US_FLUID_OUNCE = US_GALLON.register_derivative("floz", 1 / 128)
