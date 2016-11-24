============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every little
bit helps, and credit will always be given.

You can contribute in many ways:

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/lordmzn/pydmmt/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Dynamic Meta Models Tools in Python could always use more documentation, whether as part of the
official Dynamic Meta Models Tools in Python docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/lordmzn/pydmmt/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `pydmmt` for
local development.

1. Fork_ the `pydmmt` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@github.com:your_name_here/pydmmt.git

3. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

Now you can make your changes locally.

4. Create a local environment to run locally your unit tests, and install tox
   in it::

    $ cd root_of_the_repository
    $ virtualenv DEV
    $ . DEV/bin/activate
    $ pip install tox
    $ deactivate

If you don't have virtualenv, just $ pip install virtualenv.

5. When you're done making changes, check that your changes pass style and unit
   tests, including testing other Python versions with tox::

    $ . DEV/bin/activate
    $ tox
    $ deactivate

6. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

.. _Fork: https://github.com/lordmzn/pydmmt/fork

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.5, and for PyPy.
   Check https://travis-ci.org/lordmzn/pydmmt
   under pull requests for active pull requests or run the ``tox`` command and
   make sure that the tests pass for all supported Python versions.


Tips
----

To run a subset of tests::

	 $ py.test test/test_pydmmt.py
