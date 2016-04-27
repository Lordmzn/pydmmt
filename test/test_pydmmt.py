"""
Tests for `pydmmt` module.
"""
import pytest
from pydmmt import pydmmt


class TestPydmmt(object):

    @classmethod
    def setup_class(cls):
        pass

    def test_something(self):
        assert pydmmt.step(5) == 6

    @classmethod
    def teardown_class(cls):
        pass
