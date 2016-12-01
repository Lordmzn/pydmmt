"""Tests for `pydmmt` module."""
from pydmmt import pydmmt


"""
Test the functionality of the executable
"""


def test_pydmmt_as_a_calc():
    """ calc.yml """
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "examples/calc.yml"], stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.communicate("3 2".encode('utf-8'))[0]
    # trim the '\n' newline char
    print(output[:-1].decode('utf-8'))
    results = [float(l) for l in output[:-1].decode('utf-8').split()]
    assert results == [5, 9, 3, 5, 2]
    # None means it's still running; negative returncode means terminated with
    # signal -r
    assert p.returncode >= 0


def test_fibonacci():
    """ fibonacci.yml """
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "examples/fibonacci.yml"], stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.communicate(" ".encode('utf-8'))[0]
    # trim the '\n' newline char
    print(output[:-1].decode('utf-8'))
    results = [float(l) for l in output[:-1].decode('utf-8').split()]
    assert results[0:2] == [144, 89]
    assert abs(results[2] - 1.6180339887) < 0.001
    assert p.returncode >= 0


def test_fibonacci_simulation_data():
    """ fibonacci.yml plus production of simulation data file """
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    output = model.process_input(" ")
    print(output)
    # analyze simulation data produce
    from pathlib import Path
    import csv
    # simulation contains only F
    simfile = Path("simulation.log")
    assert simfile.is_file()
    # read sim_data_file
    with simfile.open() as f:
        spamreader = csv.reader(f)
        lines = 0
        for row in spamreader:
            assert len(row) == 2  # ['# t', 'F']
            lines += 1
    # assert n_data == expected
    assert lines == 14
    # this one instead contains F and Fidia
    simfile = Path("output/simulation.log")
    assert simfile.is_file()
    # read sim_data_file
    with simfile.open() as f:
        spamreader = csv.reader(f)
        lines = 0
        for row in spamreader:
            assert len(row) == 3  # ['# t', 'F', 'Fidia']
            lines += 1
    # assert n_data == expected
    assert lines == 14


def test_leslie():
    """ leslie.yml """
    model = pydmmt.Model({"sources": ["examples/leslie.yml"]})
    output = model.process_input("40 0 20")
    print(output)
    results = [float(l) for l in output.split()]
    assert abs(results[0] - 875.8826106880001) < 0.000001
    assert abs(results[1] - 1.333728647970054) < 0.000001


def test_leslie_dataset_file():
    """ leslie_inputs.yml with inputs """
    model = pydmmt.Model({"sources": ["examples/leslie_inputs.yml"]})
    output = model.process_input("40 0 20")
    print(output)
    results = [float(l) for l in output.split()]
    assert abs(results[0] - 3264.85815961) < 0.000001
    assert abs(results[1] - 1.30176322374) < 0.000001
    from pathlib import Path
    import csv
    # simulation contains only F
    simfile = Path("leslie.log")
    assert simfile.is_file()
    # read sim_data_file
    with simfile.open() as f:
        spamreader = csv.reader(f)
        lines = 0
        for row in spamreader:
            assert len(row) == 8  # [# t,N,n1,n2,n3,i1,i2,i3]
            lines += 1
    # assert n_data == expected
    assert lines == 12


def test_lake():
    """ test_lake.yml """
    model = pydmmt.Model({"sources": ["examples/test_lake.yml"]})
    output = model.process_input(".3")
    print(output)
    results = [float(l) for l in output.split()]
    assert abs(results[0] - 82.2109988777) < 0.000001
    assert abs(results[1] - 10.2356902357) < 0.000001
    assert abs(results[2] - 0.0) < 0.000001
    assert abs(results[3] - 9.76430976431) < 0.000001


"""
Test the internal components
"""


def test_pydmmt_timeline_construction():
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    assert not model.sim_timeline
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    assert list(range(0, 13)) == list(model.sim_timeline)


def test_pydmmt_todolist_construction():
    from pydmmt import util as ut
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    assert not model.sim_step_todo
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    assert {ut.Variable("F[t+2]"), ut.Variable("Fidia[t+2]")} == set(model.sim_step_todo)


def test_pydmmt_graph_construction():
    from pydmmt import util as ut
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    # variables: a set of elements
    assert ut.Variable("y1") in model.variable_names
    assert ut.Variable("x1") in model.variable_names
    assert ut.Variable("x2") in model.variable_names
    # functions: a dict with outputs as keys and functions as elements
    assert len(model.functions) > 0
    assert ut.Variable("y1") in model.functions
    assert model.functions[ut.Variable("y1")].original_string == "y1 = x1 + x2"
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    # variables: a dict from var names to deindexified names for which there's
    # a function in the library
    assert ut.Variable("F[t]") in model.variable_names
    assert "F" in model.variable_names.values()
    # functions: a dict with outputs as keys and functions as elements
    assert len(model.functions) > 2
    assert ut.Variable("F[1]") in model.functions
    assert model.functions[ut.Variable("F[0]")].calculate() == 0


def test_pydmmt_function_library():
    from pydmmt import util as ut
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    model._treat_input_data("3 4")
    assert model._calculate(ut.Variable("y1")) == 7
    model._treat_input_data(".1 .1")
    assert model._calculate(ut.Variable("y1")) == 0.2
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    assert model._calculate(ut.Variable("F[1]")) == 1
