#!/usr/bin/env python

import os
import sys

#from venari_api import __version__ as version
version="1.0"

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.md', 'r') as f:
    readme = f.read()

# Publish helper
if sys.argv[-1] == 'build':
    os.system('python setup.py sdist bdist_wheel')
    sys.exit(0)

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist --formats=zip')
    sys.exit(0)

if sys.argv[-1] == 'tag':
    os.system("git tag -a %s -m 'version %s'" % (version, version))
    os.system("git push --tags")
    sys.exit(0)

if sys.argv[-1] == 'publish-test':
    os.system('python setup.py sdist bdist_wheel upload -r pypitest')
    sys.exit(0)

setup(
    name='venari_api',
    packages=['venari_api','venari_api.models'],
    version=version,
    description='Python library for Venari',
    long_description=readme,
    author='Brandon Spruth',
    author_email='bsputh@gmail.com',
    license='MIT',
    zip_safe=True,
    install_requires = ['requests','python-dateutil'],
    keywords=['venari', 'api', 'security', 'software', 'dast'],
    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: Developers',
                 'Natural Language :: English',
                 'License :: OSI Approved :: MIT License',
                 'Topic :: Software Development',
                 'Topic :: Software Development :: Libraries :: Python Modules',
                 'Programming Language :: Python :: 3.6',
                 ]
)