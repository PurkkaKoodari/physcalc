import constants

HELP_SYNTAX = """PhysCalc parses input as operators and values.

Values can be constants, expressed as a number followed by an optional unit.
Numbers can be integers, integer ratios or decimal numbers.
All SI units and prefixes except for becquerel, gray, sievert and katal are supported.

Values can also be variables, expressed with their name, or previous results, expressed as [num].

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
<vars> can be one of """ + ", ".join(sorted(constants.VARS))
HELP_COMMANDS = """Commands:
!help [topic] - show help
!load <vars>  - load constants
!vars         - show variables
!reset        - reset variables and outputs
!clear        - reset output history"""
HELPS = {
    "syntax": HELP_SYNTAX,
    "greek": HELP_GREEK,
    "load": HELP_LOAD,
    "commands": HELP_COMMANDS,
}
HELP_GLOBAL = """Type expressions to compute them.
Type !help <topic> to get help on a specific topic.
Topics: """ + ", ".join(sorted(HELPS))
