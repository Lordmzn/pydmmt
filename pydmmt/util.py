"""Utilities supporting pydmmt."""
import ast
import operator as op
import re
import string

# supported operators
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg}
operators_string = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
                    ast.Div: "/", ast.Pow: "^", ast.USub: "-"}


# limit allowed range for each operation or any intermediate result
def power(a, b):
    if any(abs(n) > 100 for n in [a, b]):
        raise ValueError((a, b))
    return op.pow(a, b)
operators[ast.Pow] = power


def eval_(node):
    if isinstance(node, ast.Num):  # <number>
        return node.n
    elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
        return operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
        return operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


def parse(num_expr):
    return ast.parse(num_expr, mode='eval').body


# variables string
def is_variable(text):
    if (text[0] in string.ascii_letters and
       ('[' not in text or (text.count('[') == 1 and text.count(']') == 1))):
        return True
    return False


def is_indexed(text):
    return '[' in text


def is_relatively_indexed(text):
    return is_indexed(text) and 't' in index_of(text)


def is_absolutely_indexed(text):
    return is_indexed(text) and 't' not in index_of(text)


def de_indexify(text):
    return text.split('[')[0]


def indexify(text, index):
    return text + '[' + str(index) + ']'


def index_of(text):
    if not is_indexed(text):
        return None
    index = text.split('[')[1].split(']')[0]
    if any((l != 't' and l in string.ascii_letters) for l in index):
        raise ValueError("Using wrong index variable in " + text)
    return index


def delay_of(text):
    idx = index_of(text)
    if idx is None:
        return None
    if idx.strip() == 't':
        return '0'
    return idx.replace('t', '')


def resolve_index(text, curr):
    return curr + int(delay_of(text))


def is_operator(text):
    return text.strip() in operators_string.values()


def is_constant(text):
    return text.isnumeric()


# sorting files in human sorting
# source: http://stackoverflow.com/questions/4623446/how-do-you-sort-files-numerically
def tryint(s):
    try:
        return int(s)
    except:
        return s


def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [tryint(c) for c in re.split('([0-9]+)', s)]
