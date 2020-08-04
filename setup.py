from setuptools import setup, find_packages

setup(
    name="easyproc",
    version="0.6.0",
    license="MPL-2.0",
    description="thin abstraction on subprocess.run to simplify admin scripts",
    long_description=open("README.rst").read(),
    url="https://github.com/ninjaaron/easyproc",
    author="Aaron Christianson",
    author_email="ninjaaron@gmail.com",
    keywords="shell pipe subprcess process scripting",
    py_modules=["easyproc"],
    classifiers=["Programming Language :: Python :: 3.5"],
)
