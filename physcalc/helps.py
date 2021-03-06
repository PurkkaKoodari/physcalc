from physcalc.constants import VARS
from physcalc.context import Feature

HELP_SYNTAX = """PhysCalc parses input as operators and values.

Values can be constants, expressed as a number followed by an optional unit.
Numbers can be integers, integer ratios or decimal numbers.
All SI units and many other common ones are supported.
All SI prefixes are supported, with µX or uX for micro.

Values can also be variables, expressed with their name.
Previous results can be referred to as [num].

The following operators are supported: + - * / ^

See also: !help greek, !help vars"""

HELP_GREEK = """Greek characters can be typed as \\x, with x from this table:

 x | a b c d e f g h i j k l m n o p q r s t u v w x y z
\\x | α β γ δ ε φ γ χ ι η κ λ μ ν ω π ψ ρ σ τ υ θ   ξ   ζ

 x | A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
\\x | Α Β Γ Δ Ε Φ Γ Χ Ι Η Κ Λ Μ Ν Ω Π Ψ Ρ Σ Τ Υ Θ   Ξ   Ζ

Most characters translate to their Greek counterparts. Exceptions:
 - \\c = γ (gamma, \\g also works)
 - \\j = η (eta)
 - \\q = ψ (psi)
 - \\v = θ (theta)"""

HELP_VARS = """Variables are used by their name, not prefixed by a number.

Variables can be assigned using
var := value-expression

Undefined variables are not evaluated, but stay in the result."""

HELP_LOAD = """Usage: !load <vars>
Load variables to the context.
<vars> can be one of """ + ", ".join(sorted(VARS))

HELP_TOGGLE = f"""Usage: !toggle <feat>
Toggles a feature of the interpreter. Features:
{Feature.DEBUG.value:7s} - show parsed inputs before evaluating
{Feature.FRAC.value:7s} - use fractions for output whenever possible
{Feature.GRAPHIC.value:7s} - draw results graphically
{Feature.CONT.value:7s} - assume previous result when input starts with operator"""

HELP_SOURCE = """Usage: !source <file>
Executes <file> in the current REPL."""

HELP_AS = """Usage: !as <unit>
Prints the latest result in the given unit.
!as <unit> may also be appended to any calculation."""

HELP_COMMANDS = """Commands:
!help [topic]  - show help
!load <vars>   - load constants
!vars          - show variables
!reset         - reset variables and outputs
!clear         - reset output history
!toggle <feat> - toggle features
!as <unit>     - print in different units
!source <file> - execute file
!exit          - quit REPL"""

HELPS = {
    "syntax": HELP_SYNTAX,
    "greek": HELP_GREEK,
    "vars": HELP_VARS,
    "commands": HELP_COMMANDS,
    "load": HELP_LOAD,
    "toggle": HELP_TOGGLE,
}

HELP_GLOBAL = """Type expressions to compute them.
Type !help <topic> to get help on a specific topic.
Topics: """ + ", ".join(sorted(HELPS))
