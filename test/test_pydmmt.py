"""
Tests for `pydmmt` module.
"""
import pytest
from pydmmt import pydmmt


def test_pydmmt_as_a_calc():
    """ ./pyDMMT sum.py """
    from subprocess import Popen, PIPE, STDOUT
    p = Popen(["./pyDMMT", "sum.py"], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    output = p.communicate("3 2")
    assert output == 5
    # None means it's still running; negative returncode means terminated with
    # signal -r
    assert p.returncode >= 0


def test_fibonacci():
    """ ./pyDMMT fibonacci.py """
    execute pyDMMT fibonacci (contains already horizon + init conditions)
    read stdout
    assert stdout == 144
    assert process(pyDMMT) == dead


def test_fibonacci_simulation_data():
    """ ./pyDMMT fibonacci.py """
    ask simulation_data
    execute pyDMMT fibonacci (contains already horizon + init conditions)
    read stdout
    assert stdout == 144
    assert process(pyDMMT) == dead
    assert exist(sim_data_file)
    read sim_data_file
    assert n_data == expected


def test_leslie_dataset_file():
    """ ./pyDMMT -d dataset.csv leslie.py """
    pass
