"""Tests for `pydmmt` module."""
import pytest
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
    assert [float(l) for l in output[:-1].decode('utf-8').split()] == [5, 9]
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
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "examples/fibonacci.yml"], stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.communicate(" ".encode('utf-8'))[0]
    # trim the '\n' newline char
    print(output[:-1].decode('utf-8'))
    assert p.returncode >= 0
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
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "examples/leslie.yml"], stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.communicate("40 0 20".encode('utf-8'))[0]
    # trim the '\n' newline char
    print(output[:-1].decode('utf-8'))
    results = [float(l) for l in output[:-1].decode('utf-8').split()]
    assert abs(results[0] - 875.8826106880001) < 0.000001
    assert abs(results[1] - 1.333728647970054) < 0.000001
    assert p.returncode >= 0


def test_leslie_dataset_file():
    """ leslie_inputs.yml with inputs """
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "examples/leslie_inputs.yml"], stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.communicate("40 0 20".encode('utf-8'))[0]
    # trim the '\n' newline char
    print(output[:-1].decode('utf-8'))
    results = [float(l) for l in output[:-1].decode('utf-8').split()]
    assert abs(results[0] - 3264.85815961) < 0.000001
    assert abs(results[1] - 1.30176322374) < 0.000001
    assert p.returncode >= 0
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
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    assert not model.sim_step_todo
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    assert {"F[t+2]", "Fidia[t+2]"} == set(model.sim_step_todo)


def test_pydmmt_graph_construction():
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    # variables: a set of elements
    assert "y1" in model.variable_names
    assert "x1" in model.variable_names
    assert "x2" in model.variable_names
    # functions: a dict with outputs as keys and functions as elements
    assert len(model.functions) > 0
    assert "y1" in model.functions
    assert model.functions["y1"] == "x1 + x2"
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    # variables: a dict from var names to deindexified names for which there's
    # a function in the library
    assert "F[t]" in model.variable_names
    assert "F" in model.variable_names.values()
    # functions: a dict with outputs as keys and functions as elements
    assert len(model.functions) > 2
    assert "F[1]" in model.functions
    assert int(model.functions["F[0]"]) == 0


def test_pydmmt_function_library():
    #
    model = pydmmt.Model({"sources": ["examples/calc.yml"]})
    model._treat_input_data("3 4")
    assert model._calculate("y1") == 7
    model._treat_input_data(".1 .1")
    assert model._calculate("y1", ) == 0.2
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    assert model._calculate("F[1]") == 1
