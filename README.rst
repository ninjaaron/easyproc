easyproc
========
``easyproc`` is a wrapper on the ``subprocess`` that provides a similar
API, but attempts to reduce some of the boilerplate involved in using
the module.

It’s been tested with Python 3.4 and newer, though the ``timeout``
feature is broken in 3.4.

It can be installed with pip.

::

   $ pip install easyproc

It provides the ``Popen`` class and the ``run`` class which function
similarly to those in ``subprocess`` with a few differences:

- All streams default to strings (``subprocess`` uses bytes).
- Error checking is turned on by default. Errors should never pass
  silently. Unless explicitely silenced.
- If a string is passed as the initial arument instead of an iterable
  of arguments, it will be passed to ``shlex.split`` automatically.
- ``stdout`` and ``stderr`` always behave more or less like files. In
  some cases, they are special objects. More later.

.. contents::


Basics (and ``and Popen``)
--------------------------
Ok, now for a few examples.

.. code:: python

  >>> import easyproc as ep
  >>> ep.run('ls -lh')
  total 28K
  drwxr-xr-x 2 ninjaaron users 4.0K Aug 23  2017 easyproc.egg-info
  -rw-r--r-- 1 ninjaaron users  11K Aug 24 09:51 easyproc.py
  drwxr-xr-x 2 ninjaaron users 4.0K Aug 24 10:58 __pycache__
  -rw-r--r-- 1 ninjaaron users  983 Aug 24 10:56 README.rst
  -rw-r--r-- 1 ninjaaron users  491 Mar 26 12:53 setup.py
  CompletedProcess(args='ls -lh', returncode=0)
  >>> # ^ shlex.split the arguments.
  >>> ep.run('ls foo')
  ls: cannot access 'foo': No such file or directory
  Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    File "/home/ninjaaron/src/py/easyproc/easyproc.py", line 207, in run
      retcode = mkchecker(cmd, proc, ok_codes)()
    File "/home/ninjaaron/src/py/easyproc/easyproc.py", line 75, in check_code
      output=proc.stdout, stderr=proc.stderr)
  easyproc.CalledProcessError: Command 'ls foo' returned non-zero exit status 2.
  Command 'ls foo' returned non-zero exit status 2.
  >>> # get a crash when something doesn't work. You can either handle
  >>> # the error or set check=False
  >>> ep.run('ls foo', check=False)
  ls: cannot access 'foo': No such file or directory
  CompletedProcess(args='ls foo', returncode=None)
  >>> # normal concurrent stuff with Popen also works. Unicode defaults.
  >>> proc = ep.Popen('tr a-z A-Z', stdin=ep.PIPE, stdout=ep.PIPE)
  >>> proc.communicate('foo')
  ('FOO', None)
  >>> proc.poll()
  0

So all that stuff should is pretty standard for ``subprocess`` stuff,
aside from the differences mentioned above, ``easyproc.Popen`` is more
or less identical to ``subprocess.Popen``, so consult the `API docs`_
for more info.

.. _API docs:
  https://docs.python.org/3/library/subprocess.html#popen-constructor

``run`` and ``grab``
--------------------
As seen above, the ``run`` function works similarly to 

... more coming. This readme is in progress.
