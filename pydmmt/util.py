"""Utilities supporting pydmmt."""
import ast
import math
import numpy
import operator as op
import re
import string


class YAMLError(ValueError):
    """YAML error"""


class TextBased():
    def __repr__(self):
        return self.original_string

    def __str__(self):
        return self.original_string

    def __hash__(self):
        return hash(self.original_string)

    def __eq__(self, other):
        return self.original_string == other.original_string


class Variable(TextBased):
    def __init__(self, text):
        if type(text) is not str:
            for key, value in text.items():
                self.original_string = key
                if "length" in value.keys():
                    self.length = int(value["length"])
                break  # allow only one cycle = one variable definition
        else:
            self.original_string = text
        # this contains only basename if var is indexed
        self.name = self.original_string
        self.index = None
        self.delay = None
        self.is_relatively_indexed = False
        self.is_absolutely_indexed = False
        self.is_sliced = False

        self.value = numpy.nan

        self.is_indexed = ('[' in self.original_string and
                           ']' in self.original_string)
        if self.is_indexed:
            self.index = self.original_string.split('[')[1].split(']')[0]
            if any((l != 't' and l in string.ascii_letters)
                   for l in self.index):
                raise ValueError("Using wrong index variable in " +
                                 self.original_string)
            self.name = self.original_string.split('[')[0]
            self.is_relatively_indexed = 't' in self.index
            self.is_absolutely_indexed = 't' not in self.index
            self.is_sliced = ':' in self.index
            if self.is_relatively_indexed and not self.is_sliced:
                if self.index.strip() == 't':
                    self.delay = 0
                else:
                    self.delay = int(self.index.replace('t', ''))

    def actualize(self, index):
        if self.is_relatively_indexed:
            return Variable(self.name + '[' + str(index + self.delay) + ']')
        if self.is_absolutely_indexed:
            return self
        raise YAMLError

    @staticmethod
    def is_it(text):
        if type(text) is not str:
            for key, value in text.items():
                text = key
                break  # allow only one definition, discard the rest
        if text is None or len(text) == 0:
            return False
        if text[0] not in string.ascii_letters:
            return False
        if '[' in text:
            if text.count('[') != 1 or text.count(']') != 1:
                return False
        if '(' in text:
            if text.split('(')[0] in Function.accepted_functions:
                return False
        if text in Function.accepted_functions:
            return False
        if text in Function.accepted_keywords:
            return False
        return True


def _power(a, b):
    if any(abs(n) > 100 for n in [a, b]):
        raise ValueError((a, b))
    return op.pow(a, b)


def mean(a):
    return sum(a) / len(a)


def rbf(inputs, param, n_nodes):
    bases = []
    idx_p = 0
    for i in range(n_nodes):
        temp = []
        try:
            for inp in inputs:
                temp.append((inp - param[idx_p])**2 / param[idx_p+1]**2)
                idx_p += 2
        except TypeError as err:
            # Expecting: TypeError: 'numpy.float64' object is not iterable
            # it means there's only one input
            if "iterable" in err.args[0].split():
                # print(param)
                temp.append((inputs - param[idx_p])**2 / param[idx_p+1]**2)
                idx_p += 2
            else:
                raise err
        bases.append(math.exp(-sum(temp)))
    output = 0
    for w, base in zip(param[idx_p:idx_p+n_nodes], bases):
        output += base * w
    idx_p += n_nodes
    return output + param[idx_p]


class Function(TextBased):
    # supported operators and functions
    accepted_functions = {"sum": sum, "max": max, "min": min, "mean": mean,
                          "rbf": rbf}
    accepted_tree_nodes = ((ast.Num, ast.BinOp, ast.UnaryOp, ast.Subscript,
                           ast.Index, ast.Slice, ast.Load, ast.IfExp,
                           ast.Compare) +
                           (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                            ast.Pow, ast.USub, ast.Mod, ast.Lt, ast.Gt,
                            ast.NotEq, ast.Eq))
    accepted_keywords = {"if": None, "else": None}

    def __init__(self, text):
        self.original_string = text
        equation_sides = text.replace(')', ' ')\
                             .replace('(', ' ')\
                             .replace(',', ' ')\
                             .split('=', maxsplit=1)
        self.outputs = [Variable(el)
                        for el in equation_sides[0].split()
                        if Variable.is_it(el)]
        # take care of keyword arguments for function (mean(3,5,w=23))
        self.inputs = [Variable(el.split('=')[-1])
                       for el in equation_sides[1].split()
                       if Variable.is_it(el.split('=')[-1])]

        # parse the text and store the result
        # power operator: change ^ in **
        text = text.split('=', maxsplit=1)[1].lstrip()
        text = text.replace('^', '**')
        try:
            tree = ast.parse(text, mode="eval")
        except SyntaxError as exc:
            print("While parsing:", text, ";")
            raise exc
        tree.lineno = 0
        tree.col_offset = 0
        if not Function._check_tree(tree, self.inputs):
            print("While parsing of:", text, ";")
            raise YAMLError("I'm screwed")
        tree = Function.SubstituteVariables(self).visit(tree)
        ast.fix_missing_locations(tree)
        a_useful_name = ("<util.py: compiling function " +
                         self.original_string + ">")
        self.compiled = compile(tree, filename=a_useful_name, mode="eval")

    @staticmethod
    def _check_tree(tree, variables):
        # Expression(body=UnaryOp(left=Name(id='x1', ctx=Load()), op=USub()))])
        for node in ast.walk(tree.body):
            if isinstance(node, Function.accepted_tree_nodes):
                continue
            elif isinstance(node, ast.Call):
                if node.func.id not in Function.accepted_functions:
                    print("call", ast.dump(node))  # TODO
                    return False
                continue
            elif isinstance(node, ast.keyword):
                continue
            elif isinstance(node, ast.Name):
                if node.id in Function.accepted_functions:
                    continue
                if Variable(node.id) not in variables:
                    if node.id not in [v.name for v in variables]:
                        if node.id != 't':
                            print("name", node.id)  # TODO
                            return False
            else:
                print("else", ast.dump(node))  # TODO
                return False
        return True

    class SubstituteVariables(ast.NodeTransformer):
        def __init__(self, funct):
            ast.NodeTransformer.__init__(self)
            self.f = funct

        def visit_Subscript(self, node):
            # substitute names with variables
            # rebuild string of variable
            var_str = node.value.id
            if isinstance(node.slice, ast.Index):
                var_str += '['
                # if var[t+1]
                if isinstance(node.slice.value, ast.BinOp):
                    var_str += 't'
                    if isinstance(node.slice.value.op, ast.Add):
                        var_str += '+' + str(node.slice.value.right.n)
                    elif isinstance(node.slice.value.op, ast.Sub):
                        var_str += '-' + str(node.slice.value.right.n)
                # else if var[t]
                elif isinstance(node.slice.value, ast.Name):
                    var_str += 't'
                # else if var[9]
                elif isinstance(node.slice.value, ast.Num):
                    var_str += str(node.slice.value.n)
                var_str += ']'
            # if var[1:12] or var[:12] or var [123:]
            if isinstance(node.slice, ast.Slice):
                var_str += '['
                if isinstance(node.slice.lower, ast.Num):
                    if isinstance(node.slice.upper, ast.Num):
                        var_str += (str(node.slice.lower.n) + ':' +
                                    str(node.slice.upper.n))
                    elif not node.slice.upper:
                        var_str += str(node.slice.lower.n) + ':'
                elif isinstance(node.slice.upper, ast.Num):  # but not lower
                    var_str += ':' + str(node.slice.upper.n)
                elif not node.slice.lower and not node.slice.upper:
                    # they're there but equal to None
                    var_str += ':'
                else:
                    raise NotImplementedError(ast.dump(node))
                var_str += ']'
            if Variable(var_str) not in self.f.inputs:
                print(Variable(var_str), "in", self.f.inputs)  # TODO
                raise YAMLError(ast.dump(node))
            text = ("self.inputs[" +
                    str(self.f.inputs.index(Variable(var_str))) +
                    "].value")
            new_node = ast.parse(text, mode="eval").body
            ast.copy_location(new_node, node)
            ast.fix_missing_locations(new_node)
            # print(ast.dump(new_node))  # TODO
            return new_node

        def visit_Name(self, node):
            # substitute names with variables - works only for non subscript
            if node.id in Function.accepted_functions:
                return node
            if Variable(node.id) not in self.f.inputs:
                raise YAMLError(ast.dump(node))
            text = ("self.inputs[" +
                    str(self.f.inputs.index(Variable(node.id))) +
                    "].value")
            new_node = ast.parse(text, mode="eval").body
            ast.copy_location(new_node, node)
            ast.fix_missing_locations(new_node)
            # print(ast.dump(new_node))  # TODO
            return new_node

    def calculate(self):
        return eval(self.compiled)


# sorting files in human sorting
# http://stackoverflow.com/questions/4623446/how-do-you-sort-files-numerically
def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    def tryint(s):
        try:
            return int(s)
        except:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', s)]
