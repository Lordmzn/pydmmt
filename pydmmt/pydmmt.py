#!/usr/bin/env python3

import ast
import operator as op

# supported operators
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
             ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
             ast.USub: op.neg}


# limit allowed range for each operation or any intermediate result
def power(a, b):
    if any(abs(n) > 100 for n in [a, b]):
        raise ValueError((a, b))
    return op.pow(a, b)
operators[ast.Pow] = power


def isVariable(string):
    return not isOperator(string) and not isConstant(string)


def isOperator(string):
    return string == '=' or string == '+'


def isConstant(string):
    return string.isnumeric()


def eval_(node):
    if isinstance(node, ast.Num):  # <number>
        return node.n
    elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
        return operators[type(node.op)](eval_(node.left), eval_(node.right))
    elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
        return operators[type(node.op)](eval_(node.operand))
    else:
        raise TypeError(node)


class Model:

    def __init__(self, params=None):
        import yaml
        if not params:
            pass
        else:
            # print(params)  # TODO
            if params["sources"]:
                data_cache = []
                for src in params["sources"]:
                    with open(src, 'r') as f:
                        data_cache.append(yaml.load(f))
                params["sources"] = data_cache

        # print(params)  # TODO

        self.parameters = dict()
        self.parameters["simulation"] = dict()
        self.parameters["simulation"]["target"] = list()
        self.parameters["simulation"]["inputs"] = list()

        self.variables = set()
        self.functions = dict()
        for source in params["sources"]:
            if not source["functions"]:
                continue
            for function in source["functions"]:
                # vertexes of the graph
                self.variables.update([el for el in function.split()
                                       if isVariable(el)])
                # print(self.variables)  # TODO
                # edges of the graph & map edges to functions
                self.loadRelationsFromString(function)
                # print(self.varsToRelations)  # TODO
                # print(self.functions)  # TODO

            # take care of simulation details
            if source["simulation"] and source["simulation"]["target"]:
                [self.parameters["simulation"]["target"].append(thing)
                    for thing in source["simulation"]["target"]]

            if source["simulation"] and source["simulation"]["inputs"]:
                [self.parameters["simulation"]["inputs"].append(thing)
                    for thing in source["simulation"]["inputs"]]


    def loadRelationsFromString(self, function):
        outputs = []
        inputs = []
        equal_found = False
        for element in function.split():
            if not equal_found:
                if not isOperator(element):
                    outputs.append(element)
                elif element == '=':
                    equal_found = True
                else:
                    # draw exception because of implicit relation
                    # like x1 + x2 = x3 + x4
                    pass
            else:
                if not isOperator(element):
                    inputs.append(element)

        self.functions.update({y: function.split('=')[1].lstrip()
                               for y in outputs})

    def processInput(self):
        try:
            current_data = input()
        except EOFError:
            return False
        # print(current_data)  # todo
        current_data = dict(zip(self.parameters["simulation"]["inputs"],
                                [float(el) for el in current_data.split()]))
        result = [self.calculate(target_variable, current_data)
                  for target_variable in self.parameters["simulation"]["target"]]
        print(' '.join([str(el) for el in result]))
        return True


    def calculate(self, target, data):
        num_expr = self.functions[target]
        for variable in num_expr.split():
            if isVariable(variable):
                # print("Var: " + str(variable))  # todo
                # print("Data: " + str(data))  # todo
                if variable in data:
                    num_expr = num_expr.replace(variable, str(data[variable]))
                #    print("Replaced: " + str(data[variable]))  # todo
                elif variable in self.functions:
                    self.calculate(self.functions[variable], data)
                else:
                    raise ValueError
        # then finally evaluate
        # print(num_expr)  # TODO
        # print(type(num_expr))  # TODO
        return eval_(ast.parse(num_expr, mode='eval').body)


if __name__ == "__main__":
    import sys
    if sys.version_info < (3, 5):
        raise SystemExit("Sorry, you need at least python 3.5." +
                         " C'mon, middle age is finished!")

    import argparse
    from _version import __version__
    parser = argparse.ArgumentParser()
    parser.add_argument('--version',
                        action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument("sources",
                        help="Any file containing the model specification",
                        type=str,
                        nargs='*')

    model = Model(vars(parser.parse_args()))
    while model.processInput():
        pass
