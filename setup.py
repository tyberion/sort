import numpy as np

from setuptools import setup, find_packages
from setuptools.extension import Extension

from Cython.Distutils import build_ext

cmdclass = { }
ext_modules = [ ]

ext_modules += [
    Extension("sort.utils", [ "sort/utils.pyx" ]),
]
cmdclass.update({ 'build_ext': build_ext })

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="sort-kruithofmc",
    version="1.0.0",
    author="Maarten Kruithof",
    author_email="maarten.kruithof@tno.nl",
    description="A python package of the SORT tracking algorithm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tyberion/sort",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU License",
        "Operating System :: OS Independent",
    ],
    include_dirs = [np.get_include()],
    cmdclass=cmdclass,
    ext_modules=ext_modules,
)