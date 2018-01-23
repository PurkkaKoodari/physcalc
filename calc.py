import atexit
import os

import parser
from constants import CONSTANTS_MATH, VARS
from context import Context, FEATURE_DEBUG
from helps import HELPS, HELP_GLOBAL, HELP_LOAD, HELP_TOGGLE
from util import MathParseError, MathEvalError
from value import Value

APPLICATION = "ρhysCalc"
VERSION = "0.2"

LAUNCH_CREDITS = APPLICATION + " REPL " + VERSION + "\nType !help for help"

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

def _run_command(context, command, *args):
    if command in COMMANDS:
        COMMANDS[command](context, args)
    else:
        print("Unknown command " + command + ". Type !help for help.")

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
    _setup_readline()
    print(LAUNCH_CREDITS)
    context = Context()
    while True:
        prompt = " " * len(str(len(context.outputs))) + " > "
        try:
            line = input(prompt).strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        if line[0] == "!":
            _run_command(context, *line.split(None))
        else:
            try:
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
            except MathParseError as ex:
                print("Syntax error: " + ex.args[0])
            except MathEvalError as ex:
                print("Error: " + ex.args[0])

if __name__ == "__main__":
    _main()
