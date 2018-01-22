import math

from value import Value, Unit

CONSTANTS_MATH = {
    "e": Value(math.e, Unit.parse("")),
    "pi": Value(math.pi, Unit.parse("")),
    "π": Value(math.pi, Unit.parse("")),
}

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
