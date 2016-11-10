"""
Tests for `pydmmt` module.
"""
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
    assert [float(l) for l in output[:-1].decode('utf-8').split()] == [144, 89]
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
    simfile = Path("simulation.log")
    assert simfile.is_file()
    # read sim_data_file
    with simfile.open() as f:
        import csv
        spamreader = csv.reader(f, delimiter=' ', quotechar='|')
        lines = 0
        for row in spamreader:
            assert len(row) == 1
            lines += 1
    # assert n_data == expected
    assert lines == 12
    simfile = Path("output/simulation.log")
    assert simfile.is_file()


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
    """ ./pydmmt -d dataset.csv leslie.py """
    pass


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
    assert {'F[t]'} == set(model.sim_step_todo)


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
    model.processInputData("3 4")
    assert model.calculate("y1") == 7
    model.processInputData(".1 .1")
    assert model.calculate("y1", ) == 0.2
    #
    model = pydmmt.Model({"sources": ["examples/fibonacci.yml"]})
    assert model.calculate("F[1]") == 1
