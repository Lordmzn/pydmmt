#!/usr/bin/env python3
"""pydmmt performs numerical simulations of dynamic systems."""

from collections import OrderedDict
import csv
import glob
import itertools
import math
import numpy
import os
import sys
# local import
import util as ut


class Model:

    def __init__(self, params=None):
        if not params:
            raise ValueError("No parameters given to Model constructor")

        if params["sources"]:
            import yaml
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
            if "functions" in source and source["functions"]:
                for function in source["functions"]:
                    item = ut.Function(function)
                    self.functions.update({y: item for y in item.outputs})
                    self.variable_names.update({y: y.name for y
                                                in item.inputs + item.outputs})

            # take care of simulation details
            if "simulation" in source and "target" in source["simulation"]:
                items = [ut.Variable(item)
                         for item in source["simulation"]["target"]
                         if ut.Variable.is_it(item)]
                self.parameters["simulation"]["target"] += \
                    [item for item in items if not item.is_relatively_indexed]

            if "simulation" in source and "inputs" in source["simulation"]:
                items = [ut.Variable(item)
                         for item in source["simulation"]["inputs"]
                         if ut.Variable.is_it(item)]
                assert not any(item.is_relatively_indexed for item in items)
                self.parameters["simulation"]["inputs"] += items
                self.input_data = {item: 0 for item in items
                                   if not item.is_indexed}

            # check for any logging requirement
            if "logging" in source:
                # create space, if it's first loggin
                if "logging" not in self.parameters:
                    self.parameters["logging"] = dict()
                # then read each logfile that has to be produced
                [self.parameters["logging"].update(
                  {filename: [ut.Variable(item)
                   for item in source["logging"][filename]]
                   })
                 for filename in source["logging"]
                 if source["logging"][filename] and
                    len(source["logging"][filename]) > 0]

            # check for any external source
            if "external" in source:
                # create space, if it's first external source found
                if "external" not in self.parameters:
                    self.parameters["external"] = list()
                # then read each logfile to produce
                self.parameters["external"] += source["external"]

        # consistency check
        if not self.parameters["simulation"]["target"]:
            raise ut.YAMLError("No target found in given YAML files")

        # simulation function sequence and database, if needed
        self._build_timeline()
        if self.sim_timeline:  # if is an instance of a dynamic model
            self._build_simulation_helpers()
            helper = {h.name for h in self.sim_step_todo}
            if "logging" in self.parameters and self.parameters["logging"]:
                for log_file in self.parameters["logging"]:
                    helper |= {h.name for h
                               in self.parameters["logging"][log_file]}
            sim_types = {'names': list(helper),
                         'formats': ['float'] * len(helper)}
            self.sim_data = numpy.full(len(self.sim_timeline), numpy.nan,
                                       dtype=sim_types)

        # load external source if any
        if "external" in self.parameters:
            for source in self.parameters["external"]:
                if not self._load_source(source):
                    self.parameters["external"].remove(source)

        # last but not least, initialize internal clock
        self.current_step = 0

    def _build_timeline(self):
        # build timeline: the sequence of steps to evaluate
        # crawl the function tree until the first variable that requires to be
        # evaluate has an absolute index.
        candidates = self.parameters["simulation"]["target"]
        index_of_targets = [int(v.index) for v in candidates
                            if v.is_absolutely_indexed]
        # print('Candidates: ' + str(candidates))  # TODO
        while not index_of_targets:
            candidates = [v for t in candidates
                          for v in self.functions[t].inputs
                          if v not in self.parameters["simulation"]["inputs"]]
            if not candidates:
                break
            # print('Candidates2: ' + str(candidates))  # TODO
            index_of_targets = [int(num)
                                for v in candidates if v.is_absolutely_indexed
                                for num in v.index.split(':') if num]

        if not index_of_targets:
            # this instance is not a dynamic model
            self.sim_timeline = None
            self.sim_step_todo = None
            self.clock_period = 0
            return False

        # find then the lowest input (if code is executed, we're in a dynamic
        # simulation and there must be an absolutely indexed input!)
        stuff = itertools.chain(self.parameters["simulation"]["inputs"],
                                self.functions.keys())
        index_of_inputs = [int(v.index) for v in stuff
                           if v.is_absolutely_indexed]
        if not index_of_inputs:
            raise ValueError("Impossible simulation asked for.")
        self.sim_timeline = list(range(min(index_of_inputs),
                                       max(index_of_targets) + 1))
        return True
        # print("self.sim_timeline: " + str(self.sim_timeline))  # TODO

    def _build_simulation_helpers(self):
        # List the target variables to be evaluated during each simulation, and
        # try to identify some repeatable simulation step. Be aware that each
        # sim_step_todo can span multiple timesteps

        # find the leaves of the simulation - an indexed target
        unindex_leaves = {v for v in self.parameters["simulation"]["target"]
                          if v.is_indexed}
        # if no target is indexed, but relies on indexed variables
        if not unindex_leaves:
            unindex_leaves = set()
            for target in self.parameters["simulation"]["target"]:
                # |= is the set union operator
                unindex_leaves |= {v for v in self.functions[target].inputs
                                   if v.is_indexed}
        if not unindex_leaves:
            raise ValueError("Impossible simulation asked for.")
        self.sim_step_todo = OrderedDict()
        # import pdb; pdb.set_trace()
        # print("unindex_leaves: " + str(unindex_leaves))  # TODO
        for leaf in unindex_leaves:
            # stupid way of using a dict...
            leaf_found = list()
            [leaf_found.append(key) for key, value
             in self.variable_names.items() if value == leaf.name]
            indexed_leaves = leaf_found
            # print("indexed_leaves: " + str(indexed_leaves))  # TODO
            precursors = list()
            # print("self.functions: " + str(self.functions)) # TODO
            for leaf in indexed_leaves:
                if leaf not in self.functions or leaf.is_absolutely_indexed:
                    continue
                precursors += [leaf]
                # print("Prec0: " + str(precursors))  # TODO
                precursors += [v for v in self.functions[leaf].inputs
                               if v.is_relatively_indexed]
                # print("Prec0: " + str(precursors))  # TODO
            # print("Prec1: ", precursors)  # TODO
            while precursors:
                dude = precursors.pop()
                if dude in self.functions:
                    precursors += [v for v in self.functions[dude].inputs
                                   if (v.is_relatively_indexed and
                                       v not in self.sim_step_todo and
                                       v not in precursors)]
                    # the dude is added only if is a target to be evaluated
                    if dude not in self.sim_step_todo:
                        self.sim_step_todo.update({dude: None})
                elif dude.is_relatively_indexed:
                    # but in a function -> leaf of the step
                    self.sim_step_todo.update({dude: None})

        index_of_todo_list = [v.delay for v in self.sim_step_todo]
        self.clock_period = max(index_of_todo_list) - min(index_of_todo_list)
        # print("self.clock_period: " + str(self.clock_period))  # TODO

    def _load_source(self, source):
        # load source content
        with open(source, "r", newline='') as input_f:
            if os.path.splitext(source)[1] == ".csv":
                return self._process_source_csv(source, input_f)

    def _process_source_csv(self, source, input_f):
        if not self.sim_timeline:
            print("Ignoring useless ", source)
            return
        # read csv and store data in sim_data
        reader = csv.reader(input_f)
        # read first row and check if there's the t column
        headers = next(reader)
        if headers[0][0] != '#':
            print("Can't find the header for", source)
            return False
        # remove the "# " part and check for t
        headers[0] = headers[0][2:]
        if "t" not in headers:
            print("Can't find the 't' column in", source)
            return False
        # these items requires new space in self.sim_data
        headers_to_add = [h for h in headers
                          if (h not in self.sim_data.dtype.names and h != "t")]
        if headers_to_add:
            sim_types = {'names': list(headers_to_add),
                         'formats': ['float'] * len(headers_to_add)}
            new_stuff = numpy.full(len(self.sim_timeline), numpy.nan,
                                   dtype=sim_types)
            import numpy.lib.recfunctions as rfn
            self.sim_data = rfn.merge_arrays([self.sim_data, new_stuff],
                                             flatten=True,
                                             usemask=False)
        # then insert each line of data into the internal container
        for row in reader:
            for header, item in zip(headers, row):
                if header == "t":
                    try:
                        t = self.sim_timeline.index(int(item))
                        continue
                    except ValueError:
                        # current model doesn't need data from this row
                        break
                self.sim_data[header][t] = item
        return True

    def process_input(self, input_data):
        self._treat_input_data(input_data)
        # perform the simulation, if the current model requires it
        if self.sim_timeline:
            self.run_simulation()
        # finally evaluate the target variables
        result = [self._calculate(y) for y
                  in self.parameters["simulation"]["target"]]
        # save simulation file
        if "logging" in self.parameters:
            self.print_logs()
        # deliver results
        return ' '.join([str(el) for el in result])

    def run_simulation(self):
        # should be for each clock, not for each timestep
        for t in self.sim_timeline:
            self.current_step = t
            # print("sim step " + str(t))  # TODO
            for v in self.sim_step_todo:
                curr_idx = v.delay + self.current_step
                if curr_idx > self.sim_timeline[-1]:
                    continue
                # print("targetting", v.actualize(self.current_step))  # TODO
                value = self._calculate(v)
                self.sim_data[v.name][curr_idx] = value
                # print("self.sim_data:", self.sim_data)  # TODO

    def _treat_input_data(self, data):
        data = data.split()
        for v in self.parameters["simulation"]["inputs"]:
            if hasattr(v, "length"):
                # extract the required data
                try:
                    el = tuple([float(data.pop(0)) for _ in range(v.length)])
                except IndexError as err:
                    msg = "pop from empty list"
                    if err.args[0][-len(msg):] == msg:
                        self.shutdown()
            else:
                el = float(data.pop(0))  # it's scalar
            # if indexed, add the info also to sim_data
            if self.sim_timeline and v.is_indexed:
                self.sim_data[v.name][int(v.index)] = el
            self.input_data[v] = el
        # print("self.input_data:", self.input_data)  # TODO

    def _calculate(self, target, delta_t=0):
        t = self.current_step + delta_t
        # print("calculating", target, "at t =", t)  # TODO
        # given as input to the program
        if target in self.parameters["simulation"]["inputs"]:
            if target.is_indexed:
                return self.sim_data[target][int(target.index)]
            else:
                return self.input_data[target]
        # already calculated
        if self.sim_timeline and target.name in self.sim_data.dtype.names:
            idx = 0
            try:  # pythonic way? better ask for forgiveness than permission?
                try:
                    idx = target.delay + t
                except TypeError:  # has no delay field => absolute index
                    assert target.is_absolutely_indexed
                    idx = int(target.index)
                value = self.sim_data[target.name][idx]
                if not math.isnan(value):
                    # print("for", target, "found", value)  # TODO
                    return value
            except ValueError:  # is sliced!
                assert target.is_sliced
                stuff = [int(s) for s in target.index.split(':') if s]
                # splat operator (LOL)
                value = self.sim_data[target.name][slice(*stuff)]
                if not any(math.isnan(v) for v in value):
                    # print("for", target, "found", value)  # TODO
                    return value
                else:
                    ValueError("nan found for ", target, "in:", value)

        # if to be calculated
        if target in self.functions:
            # collect the inputs required
            required_variables = self.functions[target].inputs
            for v in required_variables:
                v.value = self._calculate(v, delta_t)
                if (v.is_indexed and not v.is_sliced and
                        v.name in self.sim_data.dtype.names):
                    try:
                        self.sim_data[v.name][t + v.delay] = v.value
                    except TypeError as err:
                        if err.args[0][:24] != "unsupported operand type":
                            raise err
                        assert v.is_absolutely_indexed
                        self.sim_data[v.name][t] = v.value
            # then calculate
            return self.functions[target].calculate()
        # if is relatively indexed but the current value is in the functions
        if target.is_relatively_indexed:
            actualized_target = target.actualize(t)
            if actualized_target in self.functions:
                return self._calculate(actualized_target, delta_t)
        # if we reach this point, there's an issue in the yaml
        # the issue might be: we want to calculate x[t+3] but the function
        # saved is for x[t] (and ofc we have everything to calculate x[t])
            s = 0
            for i in list(range(1, 10)):  # -1 1 -2 2 -3 3 -4 4 -5
                if i % 2 == 0:
                    s += i
                else:
                    s -= i
                delay = target.delay + s
                if delay > 0:
                    delay = 't+' + str(delay)
                elif delay == 0:
                    delay = 't'
                else:
                    delay = 't' + str(delay)
                alternative_target = ut.Variable(target.name + '[' +
                                                 delay + ']')
                # print("alternative_target:", alternative_target)  # TODO
                if alternative_target in self.functions:
                    if alternative_target.delay == 0:
                        absolute_target = ut.Variable(target.name + '[0]')
                        if absolute_target in self.functions:
                            return self._calculate(absolute_target, delta_t)
                    diff_t = target.delay - alternative_target.delay + delta_t
                    return self._calculate(alternative_target, diff_t)
        # it's the t
        if target == ut.Variable("t"):
            return t
        # eventually, give up
        raise ValueError("Variable", target, "is not evaluable.")

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
                if len(new_name) == 1 or not new_name[1].isdigit():
                    new_name = splitted_log[0] + '_1' + splitted_log[1]
                else:
                    new_name = new_name[0] + '_' + str(int(new_name[1]) + 1) \
                               + splitted_log[1]
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
            datas = [self.sim_data[d.name][t] for d in items]
            logger.writerow([t] + list(datas))

    def shutdown(self):
        sys.exit(0)


if __name__ == "__main__":
    if sys.version_info < (3, 5):
        raise SystemExit("Sorry, you need at least python 3.5.",
                         "C'mon, middle age is finished!")

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
    try:
        while True:
            print(model.process_input(input()))
    except EOFError:
        model.shutdown()
