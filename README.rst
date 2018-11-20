easyproc
========
``easyproc`` is a wrapper on the ``subprocess`` that provides a similar
API, but attempts to reduce some of the boilerplate involved in using
the module.

It's been tested with Python 3.4 and newer, though the ``timeout``
feature is broken in 3.4.

It can be installed with pip.

::

   $ pip install easyproc

It provides the ``Popen`` class and the ``run`` class which function
similarly to those in ``subprocess`` with a few differences:

- All streams default to strings (``subprocess`` uses bytes).
- Error checking is turned on by default. Errors should never pass
  silently. Unless explicitly silenced.
- If a string is passed as the initial argument instead of an iterable
  of arguments, it will be passed to ``shlex.split`` automatically.
- ``stdout`` and ``stderr`` always behave more or less like files. In
  some cases, they are special objects. More later.

The module also provides a few convenience 

.. contents::


Basics (and ``Popen``)
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
  ...
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
  >>> # crash when something doesn't work. You can either handle the
  >>> # error or set check=False
  ...
  >>> ep.run('ls foo', check=False)
  ls: cannot access 'foo': No such file or directory
  CompletedProcess(args='ls foo', returncode=None)
  >>>
  >>> # normal concurrent stuff with Popen also works. Unicode defaults.
  >>> proc = ep.Popen('tr a-z A-Z', stdin=ep.PIPE, stdout=ep.PIPE)
  >>> proc.communicate('foo')
  ('FOO', None)
  >>> proc.poll()
  0

So all that stuff should look pretty standard from ``subprocess`` usage.
Aside from the differences mentioned above, ``easyproc.Popen`` is more
or less identical to ``subprocess.Popen``, so consult the `API docs`_
for more info.

.. _API docs:
  https://docs.python.org/3/library/subprocess.html#popen-constructor

Output Streams
--------------
As seen above, the ``run`` function works similarly to the
``subprocess`` equivalent. However, when you capture the output, you
don't get text on the ``.stdout`` and ``.strerr`` attributes. The proper
way to think of Unix command output is not blocks of text, but rather
streams of lines, like a text file. (These lines may contain fields, but
that isn't the concern of ``easyproc``).

For this reason, process output is a ``ProcStream`` instance. If you use
``str()`` on it, you get the string of the process output. However, if
you iterate on it, you get lines from the file (with trailing newline
removed). It also has a context manager, but you won't need to access it
directly if you use either of those forms patterns.

.. code:: python

  >>> import easyproc as ep
  >>> procstream = ep.run("ls -sh", stdout=ep.PIPE).stdout
  >>> # ^ PIPE constant has same usage as in subprocess
  ... 
  >>> for line in procstream:
  ...     print(repr(line))
  ... 
  'total 48K'
  '4.0K easyproc.egg-info'
  ' 12K easyproc.py'
  ' 20K LICENSE'
  '4.0K __pycache__'
  '4.0K README.rst'
  '4.0K setup.py'
  >>> # the stream is used up after you iterate on it.
  ...
  >>> procstream = ep.run("ls -sh", stdout=ep.PIPE).stdout
  >>> print(procstream)
  total 52K
  4.0K easyproc.egg-info
   12K easyproc.py
   20K LICENSE
  4.0K __pycache__
  8.0K README.rst
  4.0K setup.py
  >>> # print calls str() implicitly.
