#!/usr/bin/python

import os
import glob
import unittest
import doctest
import logging

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# hide logging output
logging.basicConfig(filename="/dev/null")

# Find the test/ directory
testdir = os.path.dirname(os.path.abspath(__file__))
doctests = glob.glob(os.path.join(testdir, "*.rst"))

# Create a test suite to run all tests
suite = doctest.DocFileSuite(*doctests, module_relative=False, globs={"sys": sys})
del sys

# Add all of the tests from each file that ends with "-test.py"
for fname in os.listdir(testdir):
	if fname.endswith("-test.py"):
		fname = os.path.basename(fname)[:-3] # Get the filename and chop off ".py"
		module = __import__(fname)
		suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(module))

# Run all of the tests
unittest.TextTestRunner(verbosity=2).run(suite)
