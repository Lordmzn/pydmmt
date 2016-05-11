"""
Tests for `pydmmt` module.
"""
import pytest
from pydmmt import pydmmt


def test_pydmmt_as_a_calc():
    """ sum.py """
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["pydmmt/pydmmt.py", "sum.py"], stdin=PIPE, stdout=PIPE,
              stderr=STDOUT)
    output = p.communicate("3 2".encode('utf-8'))[0]
    # trim the '\n' newline char
    assert output[:-1].decode('utf-8') == 5
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
