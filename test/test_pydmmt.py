"""
Tests for `pydmmt` module.
"""
import pytest
from pydmmt import pydmmt


"""
Test the functionality of the executable
"""


def test_pydmmt_as_a_calc():
    """ sum.py """
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "examples/sum.yml"], stdin=PIPE,
              stdout=PIPE, stderr=STDOUT)
    output = p.communicate("3 2".encode('utf-8'))[0]
    # trim the '\n' newline char
    print(output.decode('utf-8'))
    assert float(output[:-1].decode('utf-8')) == 5
    # None means it's still running; negative returncode means terminated with
    # signal -r
    assert p.returncode >= 0


def test_fibonacci():
    """ fibonacci.py """
    # execute pydmmt fibonacci (contains already horizon + init conditions)
    # read stdout
    # assert stdout == 144
    # assert process(pydmmt) == dead
    pass


def test_fibonacci_simulation_data():
    """ fibonacci.py """
    # build simulation_data
    # execute pydmmt fibonacci (contains already horizon + init conditions)
    # read stdout
    # assert stdout == 144
    # assert process(pydmmt) == dead
    # assert exist(sim_data_file)
    # read sim_data_file
    # assert n_data == expected
    pass


def test_leslie_dataset_file():
    """ ./pydmmt -d dataset.csv leslie.py """
    pass


"""
Test the graph construction
"""


def test_pydmmt_graph_construction():
    model = pydmmt.Model({"sources": ["examples/sum.yml"]})
    # variables: a set of elements
    assert "y[i]" in model.variables
    assert "x1[i]" in model.variables
    assert "x2[i]" in model.variables
    # functions: a dict with outputs as keys and functions as elements
    assert len(model.functions) > 0
    assert "y[i]" in model.functions
    assert model.functions["y[i]"] == "x1[i] + x2[i]"


def test_pydmmt_function_library():
    model = pydmmt.Model({"sources": ["examples/sum.yml"]})
    assert model.calculate("y[i]", {"x1[i]": 3, "x2[i]": 4}) == 7
    assert model.calculate("y[i]", {"x1[i]": 0.1, "x2[i]": 0.1}) == 0.2
