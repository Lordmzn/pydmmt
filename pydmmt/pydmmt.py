#!/usr/bin/env python3
"""pydmmt performs numerical simulations of dynamic systems."""

import csv
import glob
import itertools
import math
import numpy
import os
# local import
import util as ut

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
                self._load_relations_from_string(function)

            # take care of simulation details
            if "simulation" in source and "target" in source["simulation"]:
                [self.parameters["simulation"]["target"].append(thing)
                 for thing in source["simulation"]["target"]
                 if ut.is_variable(thing) and not ut.is_relatively_indexed(thing)]

            if "simulation" in source and "inputs" in source["simulation"]:
                [self.parameters["simulation"]["inputs"].append(thing)
                 for thing in source["simulation"]["inputs"]
                 if ut.is_variable(thing) and not ut.is_relatively_indexed(thing)]

            # check for any logging requirement
            if "logging" in source:
                # create space, if it's first loggin
                if "logging" not in self.parameters:
                    self.parameters["logging"] = dict()
                # then read each logfile to produce
                [self.parameters["logging"].update(
                 {filename: source["logging"][filename]})
                 for filename in source["logging"]
                 if source["logging"][filename]
                 and len(source["logging"][filename]) > 0]

        # consistency check
        if not self.parameters["simulation"]["target"]:
            raise YAMLError("No target found in given YAML files")
        if any(ut.is_relatively_indexed(t) for t
               in self.parameters["simulation"]["target"]):
            raise YAMLError("Target " + str([ut.is_relatively_indexed(t) for t
                            in self.parameters["simulation"]["target"]])
                            + " has unspecified index")

        # simulation function sequence and database, if needed
        self._build_timeline()
        if self.sim_timeline:  # if is an instance of a dynamic model
            self._build_simulation_helpers()
            helper = {ut.de_indexify(v) for v in self.sim_step_todo}
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

    def _load_relations_from_string(self, function):
        outputs = []
        inputs = []
        equal_found = False
        for element in function.split():
            if not equal_found:
                if ut.is_variable(element):
                    outputs.append(element)
                elif element == '=':
                    equal_found = True
                else:
                    raise YAMLError("What is this '" + element + "'?")
            else:
                if ut.is_variable(element):
                    inputs.append(element)

        # power operator: change ^ in **
        function = function.replace('^', '**')
        self.functions.update({y: function.split('=')[1].lstrip()
                               for y in outputs})
        self.variable_names.update({y: ut.de_indexify(y) for y in inputs+outputs})

    def _build_timeline(self):
        # build timeline: the sequence of steps to evaluate
        # crawl the function tree until the first variable that requires to be
        # evaluate has an absolute index.
        candidates = self.parameters["simulation"]["target"]
        index_of_targets = [int(ut.delay_of(v)) for v in candidates
                          if ut.is_absolutely_indexed(v)]
        # print('Candidates: ' + str(candidates))  # TODO
        while not index_of_targets:
            candidates = [v for t in candidates
                          for v in self.functions[t].split()
                          if (ut.is_variable(v) and
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
            index_of_targets = [int(ut.delay_of(v)) for v in candidates
                              if ut.is_absolutely_indexed(v)]
        if not index_of_targets:
            # this instance is not a dynamic model
            self.sim_timeline = None
            self.sim_step_todo = None
            self.clock_period = 0
            return False

        # find then the lowest input (if code is executed, we're in a dynamic
        # simulation and there must be an absolutely indexed input!)
        index_of_inputs = [int(ut.delay_of(v)) for v
                         in itertools.chain(self.parameters["simulation"]["inputs"],
                                            self.functions.keys())
                         if ut.is_absolutely_indexed(v)]
        if not index_of_inputs:
            raise ValueError("Impossible simulation asked for.")
        self.sim_timeline = list(range(min(index_of_inputs),
                                       max(index_of_targets) + 1))
        return True
        # print("self.sim_timeline: " + str(self.sim_timeline))  # TODO

    def _build_simulation_helpers(self):
        # List the target variables to be evaluated during each simulation, and
        # try to identify some repeatable simulation step. Be aware that each
        # sim_step_todo can span multiple timesteps

        # find the leaves of the simulation - an indexed target
        unindex_leaves = {ut.de_indexify(v) for v
                          in self.parameters["simulation"]["target"]
                          if ut.is_indexed(v)}
        # if no target is indexed, but relies on indexed variables
        if not unindex_leaves:
            unindex_leaves = set()
            for target in self.parameters["simulation"]["target"]:
                # |= is the set union operator
                unindex_leaves |= {ut.de_indexify(v) for v
                                   in self.functions[target].split()
                                   if ut.is_variable(v) and ut.is_indexed(v)}
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
                if leaf not in self.functions or ut.is_absolutely_indexed(leaf):
                    continue
                precursors += [leaf]  # |= is the set union operator
                # print("Prec0: " + str(precursors))  # TODO
                precursors += [v for v in self.functions[leaf].split()
                               if ut.is_variable(v) and ut.is_relatively_indexed(v)]
                # print("Prec0: " + str(precursors))  # TODO
            # print("Prec1: " + str(precursors))  # TODO
            while precursors:
                dude = precursors.pop()
                if dude in self.functions:
                    precursors += [v for v in self.functions[dude].split()
                                   if (ut.is_variable(v) and ut.is_relatively_indexed(v)
                                       and v not in self.sim_step_todo and
                                       v not in precursors)]
                    # the dude is added only if is a target to be evaluated
                    if dude not in self.sim_step_todo:
                        self.sim_step_todo.append(dude)
                # print("Prec2: " + str(precursors))  # TODO
                # print("sim_step_todo0: " + str(self.sim_step_todo))  # TODO

        # print("sim_step_todo1: " + str(self.sim_step_todo))  # TODO
        # then
        index_of_todo_list = [int(ut.delay_of(v)) for v in self.sim_step_todo]
        self.clock_period = max(index_of_todo_list) - min(index_of_todo_list)
        # print("self.clock_period: " + str(self.clock_period))  # TODO

    def process_input(self):
        try:
            input_data = input()
        except EOFError:
            return False
        self._treat_input_data(input_data)
        # perform the simulation, if the current model requires it
        if self.sim_timeline:
            self.run_simulation()
        # finally evaluate the target variables
        result = [self._calculate(target_variable)
                  for target_variable
                  in self.parameters["simulation"]["target"]]
        # save simulation file
        if "logging" in self.parameters:
            self.print_logs()
        # deliver results
        print(' '.join([str(el) for el in result]))
        return True

    def run_simulation(self):
        # should be for each clock, not for each timestep
        for t in self.sim_timeline:
            self.current_step = t
            # print("sim step " + str(t))  # TODO
            for v in self.sim_step_todo:
                currIdx = ut.resolve_index(v, self.current_step)
                if currIdx > self.sim_timeline[-1]:
                    continue
                absVar = ut.indexify(ut.de_indexify(v), currIdx)
                # print("calculating " + absVar)  # TODO
                value = self._sim_calculate(absVar)
                self.sim_data[ut.de_indexify(v)][currIdx] = value
                # print("self.sim_data: " + str(self.sim_data))  # TODO

    def _treat_input_data(self, data):
        # if is not an instance of a dynamic model
        if not self.sim_timeline:
            for v, el in zip(self.parameters["simulation"]["inputs"],
                             (float(el) for el in data.split())):
                self.sim_data[ut.de_indexify(v)] = el
        #    print("self.sim_data: " + str(self.sim_data))  # TODO
            return
        # otherwise: dynamic inputs
        for v, el in zip(self.parameters["simulation"]["inputs"],
                         (float(el) for el in data.split())):
        #    print("v,el: " + str(v) + " = " + str(el)) # TODO
            self.sim_data[ut.de_indexify(v)][ut.resolve_index(v, self.current_step)] = el
        # print("self.sim_data: " + str(self.sim_data))  # TODO

    def _sim_calculate(self, target):
        # transform the absolute reference to the relative counterpart for
        # which we have the function in the library
        if target not in self.functions:
            target_deidx = ut.de_indexify(target)
            # stupid way of using a dict...
            for key, value in self.variable_names.items():
                if (ut.is_relatively_indexed(key) and
                    value == target_deidx and
                    key in self.functions):
                    target = key
                    break

        if target not in self.functions:
            raise ValueError("Variable " + target + " is not evaluable.")
        # print("target " + str(target))  # TODO
        num_expr = self.functions[target]
        # print("num_expr " + str(num_expr))  # TODO
        variables = [v for v in num_expr.split() if ut.is_variable(v)]
        for variable in variables:
            # if self.sim_timeline:
            #    print("dynamic sim")  # TODO
            # print(deIndexify(variable))  # TODO
            if ut.de_indexify(variable) in self.sim_data.dtype.names:
                # print("variable name with the value: " + str(ut.indexify(ut.de_indexify(variable), ut.resolve_index(variable, self.current_step))) +
                #      " when target is " + str(target) + " at time " + str(self.current_step))  # TODO
                value = self.sim_data[ut.de_indexify(variable)][ut.resolve_index(variable, self.current_step)]
                # print("value " + str(value))  # TODO
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue
                else:
                    value = self._sim_calculate(ut.indexify(ut.de_indexify(variable), ut.resolve_index(variable, self.current_step)))
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            # with absolute index
            if variable in self.functions:
                self.calculate(self.functions[variable])
                continue

            raise ValueError("Variable " + variable +
                             " is not known at evaluation time.")
        return ut.eval_(ut.parse(num_expr))

    def _calculate(self, target):
        # retrieve result from the simulation, if any
        if (self.sim_timeline and target not in self.functions and
            ut.de_indexify(target) in self.sim_data.dtype.names):
            value = self.sim_data[ut.de_indexify(target)][int(ut.index_of(target))]
            # print("value " + str(value))  # TODO
            if not math.isnan(value):
                return value
        # otherwise try to calculate
        num_expr = self.functions[target]
        variables = [v for v in num_expr.split() if ut.is_variable(v)]
        for variable in variables:
            # retrieve result from the simulation
            if (self.sim_timeline and
                ut.de_indexify(variable) in self.sim_data.dtype.names):
                if ut.is_absolutely_indexed(variable):
                    value = self.sim_data[ut.de_indexify(variable)][int(ut.index_of(variable))]
                else:
                    value = self.sim_data[ut.de_indexify(variable)][ut.resolve_index(variable, self.current_step)]
                # print("value " + str(value))  # TODO
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            # with absolute index
            if variable in self.functions:
                self.calculate(self.functions[variable])
                continue

            # this is for non dynamic simulations
            if not self.sim_timeline and ut.de_indexify(variable) in self.sim_data:
                value = self.sim_data[ut.de_indexify(variable)]
                if not math.isnan(value):
                    num_expr = num_expr.replace(variable, str(value))
                    continue

            raise ValueError("Variable " + variable +
                             " is not known at evaluation time.")
        return ut.eval_(ut.parse(num_expr))

    def print_logs(self):
        for log in self.parameters["logging"]:
            # better to ask forgiveness than permission
            try:
                with open(log, "x", newline='') as f:
                    self._write_log(f, log)
            except FileExistsError:
                # there are old logs, so add a new one
                splitted_log = os.path.splitext(log)
                old_logs = sorted(glob.glob(splitted_log[0] + "*" +
                                            splitted_log[1]),
                                  key=ut.alphanum_key)
                splitted_log = os.path.splitext(old_logs[-1])
                new_name = splitted_log[0].rsplit('_', 1)
                if len(new_name) == 1:
                    new_name = new_name[0] + '_1' + splitted_log[1]
                else:
                    new_name = new_name[0] + '_' + str(int(new_name[1]) + 1) + splitted_log[1]
                with open(new_name, "x", newline='') as f:
                    self._write_log(f, log)

            except FileNotFoundError:
                # this happens when filename contains a path, and folder on the
                # path doesn't exists
                os.makedirs(os.path.dirname(log))
                with open(log, "x", newline='') as f:
                    self._write_log(f, log)

    def _write_log(self, logfile, log_name):
        logger = csv.writer(logfile)
        items = self.parameters["logging"][log_name]
        logger.writerow(['# t'] + items)
        for t in self.sim_timeline:
            logger.writerow([self.sim_timeline[t]] +
                            list(self.sim_data[items][t]))


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
    while model.process_input():
        pass
    # print("Job done")  # TODO
