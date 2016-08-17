#!/usr/bin/env python

import os
import re
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

readme = open('README.rst').read()
doclink = """
Documentation
-------------

The full documentation is at http://pydmmt.rtfd.org."""
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

VERSIONFILE = "pydmmt/_version.py"
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

setup(
    name='pydmmt',
    version=verstr,
    description='Provides tools to construct programs that simulate dynamic ' +
                'systems of equations in Python.',
    long_description=readme + '\n\n' + doclink + '\n\n' + history,
    author='Emanuele Mason',
    author_email='emanuele.mason@polimi.it',
    url='https://github.com/lordmzn/pydmmt',
    packages=[
        'pydmmt',
    ],
    package_dir={'pydmmt': 'pydmmt'},
    include_package_data=True,
    install_requires=[
    ],
    license='MIT',
    zip_safe=False,
    keywords='pydmmt',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: PyPy',
    ]
)
