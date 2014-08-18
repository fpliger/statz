from __future__ import print_function

import sys
import os.path
from setuptools import setup, find_packages

readme = os.path.join(os.path.dirname(__file__), 'README.rst')
long_description = open(readme).read()

setup(
    name='statz',
    version='0.0.1',
    author='Fabio Pliger',
    author_email='fabio.pliger@gmail.com',
    url='',
    license='MIT',
    platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
    description='Statistics and auto-document pyramid, pytest and few other tools...',
    long_description=long_description,
    keywords='statz statistics',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "License :: OSI Approved :: MIT License",
        "Environment :: Web Environment",
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "Framework :: Pyramid",
        "Topic :: Utilities",
        "Topic :: Documentation",
        ],
    install_requires=[
        'pyramid',
    ],
    extras_require = {
      'testing': 'pytest',
      },

)