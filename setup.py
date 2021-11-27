#!/usr/bin/env python

# Standard library
from distutils.core import setup

# Local
import dbtenv


description = (
    "dbtenv lets you easily install and run multiple versions of dbt using pip with Python virtual environments,"
    " or optionally using Homebrew on Mac or Linux."
)

setup(
    name='dbtenv',
    version=dbtenv.__version__,
    description=description,
    long_description=description,
    author='Brooklyn Data Co.',
    author_email='hello@brooklyndata.co',
    url='https://github.com/brooklyn-data/dbtenv',
    packages=['dbtenv'],
    entry_points={
        'console_scripts': [
            'dbtenv = dbtenv.main:main'
        ]
    },
    python_requires='>=3.7.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'License :: OSI Approved :: Apache Software License',

        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',

        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
)
