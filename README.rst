===================================
Dynamic Meta Models Tools in Python
===================================

..
  image:: https://badge.fury.io/py/pydmmt.png
    :target: http://badge.fury.io/py/pydmmt

.. image:: https://travis-ci.org/Lordmzn/pydmmt.svg?branch=master
    :target: https://travis-ci.org/lordmzn/pydmmt

..
  image:: https://pypip.in/d/pydmmt/badge.png
    :target: https://pypi.python.org/pypi/pydmmt


Provides tools to construct programs that simulate dynamic systems of equations
in Python.


Try it now!
--------

.. image:: http://mybinder.org/badge.svg :target: http://mybinder.org:/repo/lordmzn/pydmmt


Features
--------

* Equation based model definition: just write a structured text file (`YAML
  <http://yaml.org>`_) containing the mathematical equations that
  define the model. Identify entry points as well as expected outputs.
  It's a piece of cake!

* External inputs: load data from .csv files.
  Files are identified via the keys of an associate arrays within the field
  "external" in the YAML.
  Each key represents the path to the file.
  Files are interpreted as text and must start with "# "; the rest of the first
  line is a comma separated list of strings interpreted as variable names.
  The first should be "t", the time identifies which is matched with the
  internal timeline.
  If the index "t" of a specific row is not found in the internal timeline, the
  data is discarded.
  More than one file can be given.
  Data for a single variable can be spread between files.

* External outputs: text-based logging of the computation results can be
  produced via the presence of the field "logging" in the YAML.
  Each key of the associative array contained within is interpreted as path to a
  file.
  The value of the key in the YAML should be a list of variable names, which of
  course will be written in the csv file.
