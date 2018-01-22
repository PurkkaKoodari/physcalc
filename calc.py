import atexit
import os

import parser
from constants import CONSTANTS_MATH, VARS
from helps import HELPS, HELP_GLOBAL, HELP_LOAD
from util import MathParseError, MathEvalError
from value import Value

APPLICATION = "ρhysCalc"
VERSION = "0.1"

LAUNCH_CREDITS = APPLICATION + " REPL " + VERSION + "\nType !help for help"

class Context:
    def __init__(self):
        self.outputs = []
        self.variables = dict(CONSTANTS_MATH)

def _run_command(context, command, *args):
    if command == "!help":
        if args and args[0] in HELPS:
            print(HELPS[args[0]])
        else:
            print(HELP_GLOBAL)
    elif command == "!load":
        if len(args) != 1 or args[0] not in VARS:
            print(HELP_LOAD)
        else:
            context.variables.update(VARS[args[0]])
    elif command == "!vars":
        for var in sorted(context.variables):
            print(var + " = " + str(context.variables[var]))
    elif command == "!reset":
        context.variables = dict(CONSTANTS_MATH)
        context.outputs.clear()
        print("Variables and history cleared.")
    elif command == "!clear":
        context.outputs.clear()
        print("History cleared.")
    else:
        print("Unknown command " + command + ". Type !help for help.")

def _main():
    print(LAUNCH_CREDITS)
    context = Context()
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
                code = parser.parse_input(line, context)
                print("(" + str(len(context.outputs) + 1) + ") " + str(code))
                result = code.evaluate(context, [])
                context.outputs.append(result)
                if isinstance(result, Value) and result.unit.variable is not None:
                    print("[" + str(len(context.outputs)) + "] " + str(result) + " (" + result.unit.variable + ")")
                else:
                    print("[" + str(len(context.outputs)) + "] " + str(result))
            except MathParseError as ex:
                print("Syntax error: " + ex.args[0])
            except MathEvalError as ex:
                print("Error: " + ex.args[0])

if __name__ == "__main__":
    _main()
