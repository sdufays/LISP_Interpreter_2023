#!/usr/bin/env python3

import sys
import os

import traceback
from cmd import Cmd

sys.setrecursionlimit(20_000)


class Frame:
    """
    initializes a new frame: an environment in which variables,
    bindings, are defined and looked up
    """

    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def define(self, name, value):
        self.bindings[name] = value

    def lookup(self, name):
        if name in self.bindings:
            return self.bindings[name]
        elif self.parent is not None:
            return self.parent.lookup(name)
        else:
            raise SchemeNameError


class Functions:
    def __init__(self, params, body, defining_frame):
        self.params = params
        self.body = body
        self.defining_frame = defining_frame


class SchemeError(Exception):
    """
    A type of exception to be raised if there is an error with a Scheme
    program.  Should never be raised directly; rather, subclasses should be
    raised.
    """

    pass


class SchemeSyntaxError(SchemeError):
    """
    Exception to be raised when trying to evaluate a malformed expression.
    """

    pass


class SchemeNameError(SchemeError):
    """
    Exception to be raised when looking up a name that has not been defined.
    """

    pass


class SchemeEvaluationError(SchemeError):
    """
    Exception to be raised if there is an error during evaluation other than a
    SchemeNameError.
    """

    pass


############################
# Tokenization and Parsing #
############################


def number_or_symbol(value):
    """
    Helper function: given a string, convert it to an integer or a float if
    possible; otherwise, return the string itself

    >>> number_or_symbol('8')
    8
    >>> number_or_symbol('-5.32')
    -5.32
    >>> number_or_symbol('1.2.3.4')
    '1.2.3.4'
    >>> number_or_symbol('x')
    'x'
    """
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def tokenize(source):
    """
    Splits an input string into meaningful tokens (left parens, right parens,
    other whitespace-separated values).  Returns a list of strings.

    Arguments:
        source (str): a string containing the source code of a Scheme
                      expression
    """

    def add_token():
        nonlocal ind_token
        if ind_token:
            tokens.append(ind_token)
            ind_token = ""

    tokens = []
    ind_token = ""  # holds sequence of chars that are a token
    index = 0

    while index < len(source):  # iterate through exp
        char = source[index]

        if char == ";":
            while index < len(source) and source[index] != "\n":
                index += 1  # increment index until it's past the next line
            continue

        if char in ("(", ")"):
            add_token()
            tokens.append(char)
        elif char not in (" ", "\n"):
            ind_token += char
        else:  # if token isn't empty, white space or new line
            add_token()
        index += 1

    # adding last token if it's not empty
    add_token()
    return tokens


# def tokenize(exp):
#     """
#     >>> tokenize("(x * (2 + 3))")
#     ['(', 'x', '*', '(', '2', '+', '3', ')', ')']
#     >>> tokenize("(-200.5 + x)")
#     ['(', '-200.5', '+', 'x', ')']
#     >>> tokenize("(y * -2)")
#     ['(', 'y', '*', '-2', ')']
#     """

#     tokens = []
#     number = ""  # holds sequence of tokens that are a number
#     symbols = set(["(", ")", "+", "-", "*", "/", "**"]
#    #all possible symbols as a set
#     index = 0

#     while index < len(exp):  # iterate through exp
#         char = exp[index]

#         # so that the ** is counted as one symbol
#         if index < len(exp) - 1 and exp[index : index + 2] == "**":
#             tokens.append("**")
#             index += 2
#             continue

#         # if char is a number
#         if char.isdigit() or char == ".":
#             number += char
#         elif char == "-" and (
#             index == 0 or exp[index - 1] in symbols or exp[index - 1] == " "
#         ):
#             number += char
#         else:
#             if number:
#                 tokens.append(number)
#                 number = ""  # reset number to an empty string
#             if char in symbols or char.isalpha():
#                 tokens.append(char)
#         index += 1

#     if number:
#         tokens.append(number)
#     return tokens


def parse(tokens):
    """
    Parses a list of tokens, constructing a representation where:
        * symbols are represented as Python strings
        * numbers are represented as Python ints or floats
        * S-expressions are represented as Python lists

    Arguments:
        tokens (list): a list of strings representing tokens
    """

    def parse_expression(index):
        token = tokens[index]
        if token == "(":
            sub_expr_list = []
            index += 1
            while index < len(tokens) and tokens[index] != ")":
                sub_expr, index = parse_expression(index)
                sub_expr_list.append(sub_expr)
                if index >= len(tokens):
                    raise SchemeSyntaxError()
            if index >= len(tokens):
                raise SchemeSyntaxError
            return sub_expr_list, index + 1  # past )
        elif token == ")":  # unmatched
            raise SchemeSyntaxError()
        else:
            return number_or_symbol(token), index + 1

    result, next_index = parse_expression(0)
    if next_index != len(tokens):
        raise SchemeSyntaxError

    return result

# def parse(tokens):
#     """
#     >>> tokens = tokenize("(x * (2 + 3))")
#     >>> parse(tokens)
#     Mul(Var('x'), Add(Num(2), Num(3)))
#     """
# def parse_expression(index):
#     token = tokens[index]
#     operators = {"+": Add, "-": Sub, "*": Mul, "/": Div, "**": Pow}

#     # check if token (excluding negatives and decimals) is a valid number
#     if token.replace(".", "", 1).isdigit() or (
#         token.startswith("-") and token[1:].replace(".", "", 1).isdigit()
#     ):
#         value = float(token) if "." in token else int(token)
#         return (Num(value), index + 1)

#     # if token is a variable
#     elif token.isalpha():
#         return (Var(token), index + 1)

#     elif token == "(":
#         left, next_index = parse_expression(index + 1)
#         while tokens[next_index] != ")":
#             operator = operators[tokens[next_index]]
#             next_index += 1
#             right, next_index = parse_expression(next_index)
#             left = operator(left, right)
#         return left, next_index + 1

# parsed_expression, _ = parse_expression(0)
# return parsed_expression


######################
# Built-in Functions #
######################


def divide(args):
    if len(args) == 0:
        return 1
    result = args[0]
    for arg in args[1:]:
        result /= arg
    return result


scheme_builtins = {
    "+": sum,
    "-": lambda args: -args[0] if len(args) == 1 else (args[0] - sum(args[1:])),
    "*": lambda args: 1 if not args else args[0] * scheme_builtins["*"](args[1:]),
    "/": divide,
}


##############
# Evaluation #
##############


builtins_frame = Frame()
# updates bindings dict with contents of scheme_bultins
builtins_frame.bindings.update(scheme_builtins)


def evaluate(tree, frame=None):
    """
    Evaluate the given syntax tree according to the rules of the Scheme
    language.

    Arguments:
        tree (type varies): a fully parsed expression, as the output from the
                            parse function
    >>> evaluate('+')
    <built-in function sum>

    >>> evaluate(3.14)
    3.14

    >>> evaluate(['+', 3, 7, 2])
    12

    """
    if frame is None:
        frame = Frame(parent=builtins_frame)
    if isinstance(tree, (int, float)):
        return tree  # numbers
    elif isinstance(tree, str):  # variables
        if tree in scheme_builtins:  # doesn't allow for changing functions
            return scheme_builtins[tree]
        return frame.lookup(tree)

    if not tree:  # 3mpty list
        raise SchemeEvaluationError

    first, *rest = tree

    if first == "define":
        _, name_or_sig, expr = tree
        if isinstance(name_or_sig, list):  # function
            func, *params = name_or_sig
            lambda_expr = ["lambda", params, expr]
            value = evaluate(lambda_expr, frame)
            frame.define(func, value)
            return value
        else:  # variable
            value = evaluate(expr, frame)
            frame.define(name_or_sig, value)
        return value

    if first == "lambda":
        _, params, body = tree
        return Functions(params, body, frame)

    func = evaluate(first, frame)
    args = [evaluate(arg, frame) for arg in rest]

    if isinstance(func, Functions):
        if len(args) != len(func.params):
            raise SchemeEvaluationError()
        new_frame = Frame(parent=func.defining_frame)
        for param, arg in zip(func.params, args):
            new_frame.define(param, arg)
        return evaluate(func.body, new_frame)
    if callable(func):
        return func(args)

    raise SchemeEvaluationError()


def result_and_frame(expression, frame=None):
    if frame is None:
        frame = Frame(parent=builtins_frame)
    result = evaluate(expression, frame)
    return result, frame


########
# REPL #
########

try:
    import readline
except ImportError:
    readline = None


def supports_color():
    """
    Returns True if the running system's terminal supports color, and False
    otherwise.  Not guaranteed to work in all cases, but maybe in most?
    """
    plat = sys.platform
    supported_platform = plat != "Pocket PC" and (
        plat != "win32" or "ANSICON" in os.environ
    )
    # IDLE does not support colors
    if "idlelib" in sys.modules:
        return False
    # isatty is not always implemented, #6223.
    is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    if not supported_platform or not is_a_tty:
        return False
    return True


class SchemeREPL(Cmd):
    """
    Class that implements a Read-Evaluate-Print Loop for our Scheme
    interpreter.
    """

    history_file = os.path.join(os.path.expanduser("~"), ".6101_scheme_history")

    if supports_color():
        prompt = "\033[96min>\033[0m "
        value_msg = "  out> \033[92m\033[1m%r\033[0m"
        error_msg = "  \033[91mEXCEPTION!! %s\033[0m"
    else:
        prompt = "in> "
        value_msg = "  out> %r"
        error_msg = "  EXCEPTION!! %s"

    keywords = {
        "define",
        "lambda",
        "if",
        "equal?",
        "<",
        "<=",
        ">",
        ">=",
        "and",
        "or",
        "del",
        "let",
        "set!",
        "+",
        "-",
        "*",
        "/",
        "#t",
        "#f",
        "not",
        "nil",
        "cons",
        "list",
        "cat",
        "cdr",
        "list-ref",
        "length",
        "append",
        "begin",
    }

    def __init__(self, use_frames=False, verbose=False):
        self.verbose = verbose
        self.use_frames = use_frames
        self.global_frame = None
        Cmd.__init__(self)

    def preloop(self):
        if readline and os.path.isfile(self.history_file):
            readline.read_history_file(self.history_file)

    def postloop(self):
        if readline:
            readline.set_history_length(10_000)
            readline.write_history_file(self.history_file)

    def completedefault(self, text, _, begidx, endidx):
        _ = begidx
        _ = endidx
        try:
            bound_vars = set(self.global_frame)
        except AttributeError:
            bound_vars = set()
        return sorted(i for i in (self.keywords | bound_vars) if i.startswith(text))

    def onecmd(self, line):
        if line in {"EOF", "quit", "QUIT"}:
            print()
            print("bye bye!")
            return True

        elif not line.strip():
            return False

        try:
            token_list = tokenize(line)
            if self.verbose:
                print("tokens>", token_list)
            expression = parse(token_list)
            if self.verbose:
                print("expression>", expression)
            if self.use_frames:
                output, self.global_frame = result_and_frame(
                    *(
                        (expression, self.global_frame)
                        if self.global_frame is not None
                        else (expression,)
                    )
                )
            else:
                output = evaluate(expression)
            print(self.value_msg % output)
        except SchemeError as e:
            if self.verbose:
                traceback.print_tb(e.__traceback__)
                print(self.error_msg.replace("%s", "%r") % e)
            else:
                print(self.error_msg % e)

        return False

    completenames = completedefault

    def cmdloop(self, intro=None):
        while True:
            try:
                Cmd.cmdloop(self, intro=None)
                break
            except KeyboardInterrupt:
                print("^C")


if __name__ == "__main__":
    # doctest.testmod()
    SchemeREPL(use_frames=True, verbose=False).cmdloop()
