*easyproc* is based on the ``suprocess.run()`` function in Python 3.5 (a
fair amount of the code is copied directly from the module). It provides
basically the same interface, plus a couple of convenience features and
functions to simplify administrative scripting a bit. It addresses what
I perceive to be three shortcomings in the Popen API (in order of
egregiousness)

1. Input and output streams default to bytes. This is manifestly
   ridiculous in Python 3. easyproc turns on *universal_newlines*
   everywhere, so you don't have to worry about decoding bytes.
2. Piping a chain of processes together is not particularly intuitive
   and takes a lot of extra work when not using shell=True.
   ``easyproc.pipe()`` provides a simple way to pipe a chain of shell
   commands into each other without the safety risk of granting a shell.
   Admittedly, if one is piping together a lot of shell commands, one
   might wonder why bother with python at all? Or better, why not use
   native python filters? Certainly, that is the preferable option in
   situations were "shelling out" creates a performance bottle-neck, but
   there are times where the performance cost is small, and, in terms of
   development speed, shell utilities are often ideally suited to
   parsing the output of shell commands. Easy things should be easy,
   right?
3. While not particularly egregious, and sometimes even useful, it can
   be annoying to split each command argument into a separate list item.
   easyproc commands can be strings or lists. If it's a string, it's run
   through ``shlex.split()`` prior to being passed to
   ``subprocess.run()``.

Additionally, easyproc defaults to error checking. As per *The Zen of
Python*, "Errors should never pass silently -- unless explicitly
silenced." easyproc follows this logic.

*easyproc* does not replace all the functionality of the subprocess
module by a long shot, but it does try to expose much of it by passing
additional kwargs to ``subprocess.run()``, so many advanced use-cases
should be possible, and one need only refer to the documentation for the
subprocess module.

*easyproc* provides four simple functions for messing with shell
commands. ``easyproc.run()`` simply runs the command you give it through
``shlex.split()`` if it is a string, and then sends it to
``suprocess.run()`` with *universal_newlines* turned on, and all
additional kwargs passed along to Popen. As with ``subprocess.run()`` it
returns as ``CompletedProcess`` instance. The only difference is that
stdout and stderr attributes are ProcOutput instances (see below)
instead of byte-strings. Note that the "timeout" parameters is broken in
python 2.

``easyproc.Popen()`` also turns on unicode and automatically splits
command strings, but it returns a Popen instance, in case you need to
interact with a running process (Note: the Popen object will require
explicit error checking because it represents a process in progress and
doesn't have a return code until additional methods are called on it).

``easyproc.grab()`` is like ``easyproc.run()``, but it captures the
stdout of the command without the bother of having to type
``stdout=easyproc.PIPE`` and ``.stdout``. If the ``both`` parameter is
``True``, stderr will be captured in the same stream as stdin. (same as
``stderr=easyproc.STDIN``.)

``easyproc.pipe()`` takes any number of commands as args and pipes them
into each other in the order they are given. The output is captured as
with ``easyproc.grab()``, unless otherwise specified. if you plan on
passing a lot of subprocess.run/Popen parameters to easyproc.pipe, you
may want to look at the doc string to see what it will do.

*easyproc* also provides the three special variables from the subprocess
module, ``PIPE``, ``STDOUT``, and ``DEVNULL``, for those who know and
care what they do.

While the ``input`` parameter for easyproc functions is inherited
directly from ``suprocess.run()``, it may be useful for those avoiding
the subprocess docs to here note that this parameter is used to pass
text to the STDIN of a command (and doesn't require the use of
stdin=PIPE); i.e. it's like ``echo "text"|command``. In suprocess, the
text must be bytes by default. In easyproc, as with all other streams,
it ought to be a string.

All streams returned by functions in this module (i.e. stdout and
stderr), excluding Popen, are ``ProcOutput`` objects. These are
subclasses of ``str``, but they act like a tuple of (stripped) lines
when you do sequence operations on them, since most shell commands
produce output which is intended to be read line by line. Basically, the
whole reason this module exists is because I got tired of writing
``subprocess.check_output(['cmd', 'and',
'args']).decode().splitines()``. Now, I just write ``easyproc.grab('cmd
and args')``.
