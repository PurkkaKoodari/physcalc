import argparse
import atexit
import os
import sys

from physcalc import parser
from physcalc.constants import CONSTANTS_MATH, VARS
from physcalc.context import Context, FEATURE_DEBUG
from physcalc.helps import HELPS, HELP_GLOBAL, HELP_LOAD, HELP_TOGGLE, HELP_SOURCE
from physcalc.util import MathParseError, MathEvalError
from physcalc.value import Value

APPLICATION = "ρhysCalc"
VERSION = "0.2"

LAUNCH_CREDITS = APPLICATION + " REPL " + VERSION
LAUNCH_HELP = "Type !help for help"

COMMANDS = {}

def _register_command(name):
    def wrapper(func):
        COMMANDS[name] = func
        return func
    return wrapper

@_register_command("!help")
def _command_help(_, args):
    if args and args[0] in HELPS:
        print(HELPS[args[0]])
    else:
        print(HELP_GLOBAL)

@_register_command("!load")
def _command_load(context, args):
    if len(args) != 1 or args[0] not in VARS:
        print(HELP_LOAD)
    else:
        context.variables.update(VARS[args[0]])

@_register_command("!vars")
def _command_vars(context, _):
    for var in sorted(context.variables):
        print(var + " = " + context.variables[var].evaluate(context, []).stringify(context))

@_register_command("!reset")
def _command_reset(context, _):
    context.variables = dict(CONSTANTS_MATH)
    context.outputs.clear()
    print("Variables and history cleared.")

@_register_command("!clear")
def _command_clear(context, _):
    context.outputs.clear()
    print("History cleared.")

@_register_command("!toggle")
def _command_toggle(context, args):
    if args and args[0] in context.features:
        context.features[args[0]] = not context.features[args[0]]
        print("Toggled " + args[0] + " " + ["off", "on"][context.features[args[0]]] + ".")
    else:
        print(HELP_TOGGLE)

@_register_command("!source")
def _command_source(context, args):
    if args:
        _run_file(context, " ".join(args))
    else:
        print(HELP_SOURCE)

@_register_command("!exit")
def _command_exit(context, args):
    sys.exit(0)

def _run_command(context, command, *args):
    if command in COMMANDS:
        COMMANDS[command](context, args)
    else:
        print("Unknown command " + command + ". Type !help for help.")

def _run_line(context, line):
    if not line or line.startswith("#"):
        return
    if line[0] == "!":
        _run_command(context, *line.split(None))
        return
    assigns, code = parser.parse_input(line, context)
    if context.features[FEATURE_DEBUG]:
        print("(" + str(len(context.outputs) + 1) + ") " + code.stringify(context))
    result = code.evaluate(context, [])
    context.outputs.append(result)
    for variable in assigns:
        context.variables[variable.name] = result
    print("[" + str(len(context.outputs)) + "] " + result.stringify(context), end="")
    if isinstance(result, Value) and result.unit.variable is not None:
        print(" (" + result.unit.variable + ")")
    else:
        print()

def _run_file(context, file):
    try:
        with open(file, "r") as stream:
            lines = stream.readlines()
    except FileNotFoundError:
        print("File does not exist.")
        return False
    except IOError:
        print("Failed to read file.")
        return False
    for lineno, line in enumerate(lines):
        line = line.strip()
        try:
            _run_line(context, line)
        except MathParseError as ex:
            print("Syntax error on line %d: %s" % (lineno + 1, ex.args[0]))
            break
        except MathEvalError as ex:
            print("Error on line %d: %s" % (lineno + 1, ex.args[0]))
            break
    return True

def _setup_readline():
    # setup readline if on posix
    if os.name == "posix":
        try:
            import readline
            # load history file if any exists
            history_file = os.path.join(os.path.expanduser("~"), ".physcalc_history")
            try:
                readline.read_history_file(history_file)
            except FileNotFoundError:
                pass
            readline.set_history_length(1000)
            # save history file on exit
            atexit.register(readline.write_history_file, history_file)
        except ImportError:
            pass

def _main():
    argparser = argparse.ArgumentParser(description="Runs the %s REPL." % APPLICATION)
    argparser.add_argument("-v", "--version", action="store_true", help="shows the version and exits")
    argparser.add_argument("file", nargs="?", default=None, help="a script to execute in the REPL")
    args = argparser.parse_args()

    print(LAUNCH_CREDITS)
    if args.version:
        return 0

    print(LAUNCH_HELP)
    _setup_readline()
    context = Context()
    if args.file:
        if not _run_file(context, args.file):
            return 1

    while True:
        prompt = " " * len(str(len(context.outputs))) + " > "
        try:
            line = input(prompt).strip()
        except KeyboardInterrupt:
            print("Type !exit or press " + ("Ctrl-Z + Enter" if os.name == "nt" else "Ctrl-D") + " to quit.")
            continue
        except EOFError:
            print()
            break
        try:
            _run_line(context, line)
        except MathParseError as ex:
            print("Syntax error: " + ex.args[0])
        except MathEvalError as ex:
            print("Error: " + ex.args[0])

    return 0

sys.exit(_main())
