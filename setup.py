#  import numpy as np
#  
#  from distutils.core import setup
#  from Cython.Build import cythonize
#  
#  setup(
#      ext_modules = cythonize('sort_utils.pyx'),
#      include_dirs = [np.get_include()]
#  )

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sort-kruithofmc",
    version="1.0.0",
    author="Maarten Kruithof",
    author_email="maarten.kruithof@tno.nl",
    description="A python package of the SORT tracking algorithm",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tyberion/sort",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU License",
        "Operating System :: OS Independent",
    ],
)