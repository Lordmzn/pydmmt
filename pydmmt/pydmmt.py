#!/usr/bin/env python3

import ast
import itertools
import math
import numpy
import operator as op
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


def isVariable(text):
    if (text[0] in string.ascii_letters and
       ('[' not in text or (text.count('[') == 1 and text.count(']') == 1))):
        return True
    return False


def isIndexed(text):
    return '[' in text


def isRelativelyIndexed(text):
    return isIndexed(text) and 't' in indexOf(text)


def isAbsolutelyIndexed(text):
    return isIndexed(text) and not 't' in indexOf(text)


def deIndexify(text):
    return text.split('[')[0]


def indexify(text, index):
    return text + '[' + str(index) + ']'


def indexOf(text):
    if not isIndexed(text):
        return None
    index = text.split('[')[1].split(']')[0]
    if any((l != 't' and l in string.ascii_letters) for l in index):
        raise ValueError("Using wrong index variable in " + text)
    return index


def delayOf(text):
    idx = indexOf(text)
    if idx is None:
        return None
    if idx.strip() == 't':
        return '0'
    return idx.replace('t', '')


def resolveIndex(text, curr):
    return curr + int(delayOf(text))


def isOperator(text):
    return text.strip() in operators_string.values()


def isConstant(text):
    return text.isnumeric()


class YAMLError(ValueError):
    """YAML error"""


class Model:

    def __init__(self, params=None):
        import yaml
        if not params:
            pass
        else:
            if params["sources"]:
                data_cache = []
                for src in params["sources"]:
                    with open(src, 'r') as f:
                        data_cache.append(yaml.load(f))
                params["sources"] = data_cache

        self.parameters = dict()
        self.parameters["simulation"] = dict()
        self.parameters["simulation"]["target"] = list()
        self.parameters["simulation"]["inputs"] = list()

        self.variable_names = dict()  # maps deindexified name with indexed one
        self.functions = dict()
        for source in params["sources"]:
            # check for field existence and emptiness
            if "functions" not in source or not source["functions"]:
                continue
            for function in source["functions"]:
                self.loadRelationsFromString(function)

            # take care of simulation details
            if "simulation" in source and "target" in source["simulation"]:
                [self.parameters["simulation"]["target"].append(thing)
                 for thing in source["simulation"]["target"]
                 if isVariable(thing) and not isRelativelyIndexed(thing)]

            if "simulation" in source and "inputs" in source["simulation"]:
                [self.parameters["simulation"]["inputs"].append(thing)
                 for thing in source["simulation"]["inputs"]
                 if isVariable(thing) and not isRelativelyIndexed(thing)]

        # consistency check
        if not self.parameters["simulation"]["target"]:
            raise YAMLError("No target found in given YAML files")
        if any(isRelativelyIndexed(t) for t
               in self.parameters["simulation"]["target"]):
            raise YAMLError("Target " + str([isRelativelyIndexed(t) for t
                            in self.parameters["simulation"]["target"]])
                            + " has unspecified index")

        # simulation function sequence and database, if needed
        self.buildTimeline()
        if self.sim_timeline:  # if is an instance of a dynamic model
            self.buildSimulationHelpers()
            helper = {deIndexify(v) for v in self.sim_step_todo}
            sim_types = {'names': list(helper),
                         'formats': ['float'] * len(helper)}
            self.sim_data = numpy.full(len(self.sim_timeline), numpy.nan,
                                       dtype=sim_types)

        else:
            self.sim_data = {v:0 for v
                             in self.parameters["simulation"]["inputs"]}
        # print("self.sim_data: " + str(self.sim_data))  # TODO
        # internal clock
        self.current_step = 0

    def loadRelationsFromString(self, function):
        outputs = []
        inputs = []
        equal_found = False
        for element in function.split():
            if not equal_found:
                if isVariable(element):
                    outputs.append(element)
                elif element == '=':
                    equal_found = True
                else:
                    raise YAMLError("What is this '" + element + "'?")
            else:
                if isVariable(element):
                    inputs.append(element)

        # power operator: change ^ in **
        function = function.replace('^', '**')
        self.functions.update({y: function.split('=')[1].lstrip()
                               for y in outputs})
        self.variable_names.update({y: deIndexify(y) for y in inputs+outputs})

    def buildTimeline(self):
        # build timeline: the sequence of steps to evaluate
        # crawl the function tree until the first variable that requires to be
        # evaluate has an absolute index.
        candidates = self.parameters["simulation"]["target"]
        indexOfTargets = [int(delayOf(v)) for v in candidates
                          if isAbsolutelyIndexed(v)]
        # print('Candidates: ' + str(candidates))  # TODO
        while not indexOfTargets:
            candidates = [v for t in candidates
                          for v in self.functions[t].split()
                          if (isVariable(v) and
                              v not in self.parameters["simulation"]["inputs"])]
            #new_candidates = list()
            #for t in candidates:
            #    print("A candidate: " + str(t))
            #    for v in self.functions[t].split():
            #        print(v)
            #        if isVariable(v) and v not in self.parameters["simulation"]["inputs"]:
            #            new_candidates.append(v)
            #candidates = new_candidates
            if not candidates:
                break
            # print('Candidates2: ' + str(candidates))  # TODO
            indexOfTargets = [int(delayOf(v)) for v in candidates
                              if isAbsolutelyIndexed(v)]
        if not indexOfTargets:
            # this instance is not a dynamic model
            self.sim_timeline = None
            self.sim_step_todo = None
            self.clock_period = 0
            return False

        # find then the lowest input (if code is executed, we're in a dynamic
        # simulation and there must be an absolutely indexed input!)
        index_of_inputs = [int(delayOf(v)) for v
                         in itertools.chain(self.parameters["simulation"]["inputs"],
                                            self.functions.keys())
                         if isAbsolutelyIndexed(v)]
        if not index_of_inputs:
            raise ValueError("Impossible simulation asked for.")
        self.sim_timeline = list(range(min(index_of_inputs),
                                       max(indexOfTargets) + 1))
        return True
        # print("self.sim_timeline: " + str(self.sim_timeline))  # TODO

    def buildSimulationHelpers(self):
        # List the target variables to be evaluated during each simulation, and
        # try to identify some repeatable simulation step. Be aware that each
        # sim_step_todo can span multiple timesteps

        # find the leaves of the simulation - an indexed target
        unindex_leaves = {deIndexify(v) for v
                          in self.parameters["simulation"]["target"]
                          if isIndexed(v)}
        # if no target is indexed, but relies on indexed variables
        if not unindex_leaves:
            unindex_leaves = set()
            for target in self.parameters["simulation"]["target"]:
                # |= is the set union operator
                unindex_leaves |= {deIndexify(v) for v
                                   in self.functions[target].split()
                                   if isVariable(v) and isIndexed(v)}
        if not unindex_leaves:
            raise ValueError("Impossible simulation asked for.")
        self.sim_step_todo = list()
        # print("unindex_leaves: " + str(unindex_leaves))  # TODO
        for leaf in unindex_leaves:
            # stupid way of using a dict...
            leaf_found = list()
            for key, value in self.variable_names.items():
                if value == leaf:
                    leaf_found.append(key)
            indexed_leaves = leaf_found
            # print("indexed_leaves: " + str(indexed_leaves))  # TODO
            precursors = list()
            # print("self.functions: " + str(self.functions)) # TODO
            for leaf in indexed_leaves:
                if leaf not in self.functions or isAbsolutelyIndexed(leaf):
                    continue
                precursors += [leaf]  # |= is the set union operator
                # print("Prec0: " + str(precursors))  # TODO
                precursors += [v for v in self.functions[leaf].split()
                               if isVariable(v) and isRelativelyIndexed(v)]
                # print("Prec0: " + str(precursors))  # TODO
            # print("Prec1: " + str(precursors))  # TODO
            while precursors:
                dude = precursors.pop()
                if dude in self.functions:
                    precursors += [v for v in self.functions[dude].split()
                                   if (isVariable(v) and isRelativelyIndexed(v)
                                       and v not in self.sim_step_todo and
                                       v not in precursors)]
                    # the dude is added only if is a target to be evaluated
                    if dude not in self.sim_step_todo:
                        self.sim_step_todo.append(dude)
                # print("Prec2: " + str(precursors))  # TODO
                # print("sim_step_todo0: " + str(self.sim_step_todo))  # TODO

        # print("sim_step_todo1: " + str(self.sim_step_todo))  # TODO
        # then
        indexOfTodoList = [int(delayOf(v)) for v in self.sim_step_todo]
        self.clock_period = max(indexOfTodoList) - min(indexOfTodoList)
        # print("self.clock_period: " + str(self.clock_period))  # TODO

    def buildPeriodicTable(self): # useless right now?
        periods = dict()
        for f in self.functions:
            if not isIndexed(f) or isAbsolutelyIndexed(f):
                continue
        #    print(self.functions) #
        #    print(f) #
            idx_LHS = int(delayOf(f))
            idx_RHS = 100
            variables = [var for var in self.functions[f].split()
                         if isVariable(var)]
        #    print("vars: " + str(variables)) #
            for var in variables:
                if abs(int(delayOf(var))) < idx_RHS:
                    idx_RHS = int(delayOf(var))
            periods[f] = idx_LHS - idx_RHS
        # print("Periods found: " + str(periods)) #
        return periods

    def processInput(self):
        try:
            input_data = input()
        except EOFError:
            return False
        self.processInputData(input_data)
        if self.sim_timeline:
            # print("Simulation!")
            self.runSimulation()
        result = [self.calculate(target_variable)
                  for target_variable
                  in self.parameters["simulation"]["target"]]
        print(' '.join([str(el) for el in result]))
        return True

    def processInputData(self, data):
        if not self.sim_timeline:  # if is an instance of a dynamic model
            for v, el in zip(self.parameters["simulation"]["inputs"],
                             (float(el) for el in data.split())):
                self.sim_data[deIndexify(v)] = el
        #    print("self.sim_data: " + str(self.sim_data))  # TODO
            return
        # dynamic inputs
        for v, el in zip(self.parameters["simulation"]["inputs"],
                         (float(el) for el in data.split())):
        #    print("v,el: " + str(v) + " = " + str(el)) # TODO
            self.sim_data[deIndexify(v)][resolveIndex(v, self.current_step)] = el
        # print("self.sim_data: " + str(self.sim_data))  # TODO

    def sim_calculate(self, target):
        # transform the absolute reference to the relative counterpart for
        # which we have the function in the library
        if target not in self.functions:
            target_deidx = deIndexify(target)
            # stupid way of using a dict...
            for key, value in self.variable_names.items():
                if (isRelativelyIndexed(key) and
                    value == target_deidx and
                    key in self.functions):
                    target = key
                    break

        if target not in self.functions:
            raise ValueError("Variable " + target + " is not evaluable.")
        # print("target " + str(target))  # TODO
        num_expr = self.functions[target]
        # print("num_expr " + str(num_expr))  # TODO
        variables = [v for v in num_expr.split() if isVariable(v)]
        for variable in variables:
            # if self.sim_timeline:
            #    print("dynamic sim")  # TODO
            # print(deIndexify(variable))  # TODO
            if (self.sim_timeline and
                deIndexify(variable) in self.sim_data.dtype.names):
                # print("variable name with the value: " + str(indexify(deIndexify(variable),resolveIndex(variable, self.current_step))))  # TODO
                value = self.sim_data[deIndexify(variable)][resolveIndex(variable, self.current_step)]
                # print("value " + str(value))  # TODO
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue
                else:
                    value = self.sim_calculate(indexify(deIndexify(variable),resolveIndex(variable, self.current_step)))
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            # with absolute index
            if variable in self.functions:
                self.calculate(self.functions[variable])
                continue

            # this is for non dynamic simulations
            if not self.sim_timeline and deIndexify(variable) in self.sim_data:
                value = self.sim_data[deIndexify(variable)]
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            raise ValueError("Variable " + variable +
                             " is not known at evaluation time.")
        return eval_(ast.parse(num_expr, mode='eval').body)

    def calculate(self, target):
        # retrieve result from the simulation, if any
        if (self.sim_timeline and target not in self.functions and
            deIndexify(target) in self.sim_data.dtype.names):
            value = self.sim_data[deIndexify(target)][int(indexOf(target))]
            # print("value " + str(value))  # TODO
            if not math.isnan(value):
                return value
        # otherwise try to calculate
        num_expr = self.functions[target]
        variables = [v for v in num_expr.split() if isVariable(v)]
        for variable in variables:
            # retrieve result from the simulation
            if (self.sim_timeline and
                deIndexify(variable) in self.sim_data.dtype.names):
                value = self.sim_data[deIndexify(variable)][resolveIndex(variable, self.current_step)]
                # print("value " + str(value))  # TODO
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            # with absolute index
            if variable in self.functions:
                self.calculate(self.functions[variable])
                continue

            # this is for non dynamic simulations
            if not self.sim_timeline and deIndexify(variable) in self.sim_data:
                value = self.sim_data[deIndexify(variable)]
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            raise ValueError("Variable " + variable +
                             " is not known at evaluation time.")
        return eval_(ast.parse(num_expr, mode='eval').body)

    def runSimulation(self):
        # should be for each clock, not for each timestep
        for t in self.sim_timeline:
            self.current_step = t
            # print("sim step " + str(t))  # TODO
            for v in self.sim_step_todo:
                currIdx = resolveIndex(v, self.current_step)
                if currIdx > self.sim_timeline[-1]:
                    continue
                absVar = indexify(deIndexify(v), currIdx)
                # print("calculating " + absVar)  # TODO
                value = self.sim_calculate(absVar)
                self.sim_data[deIndexify(v)][currIdx] = value
                # print("self.sim_data: " + str(self.sim_data))  # TODO


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
    # print("Job done")  # TODO
