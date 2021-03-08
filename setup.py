#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages


setup(
    name='dbtenv',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'dbtenv = dbtenv.main:main'
        ]
    }
)
