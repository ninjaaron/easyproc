#!/usr/bin/env python3
'''
Functions to make using shell commands easier than it is with the
subprocess module, but no less safe (doesn't give the command a shell),
and still fairly "pythonic."

Basically, all the functions run shlex.split() on your command if it's a
string (though normal list commands are also supported) and they use
unicode instead of bytes (which subprocess doesn't do in python3 because
why?). Of course, these functions are no substitute for the full power
of the Popen interface, though it will pass additional kwargs to
subprocess.run(), so you can still do some Popen stuff.

If you are a shell fanatic, you may want to take note of the special
'input' parameter, which allows you to pipe a string to the stdin of
your process (normally bytes, but string with this module).

Also, use 'check=True' to catch errors.

For stream redirection and all that jazz, refer to the subprocess
documentation. I took the liberty of bringing the PIPE, DEVNULL and
STDOUT directly into this module from subprocess, for those who know and
care what those are for.
'''
import subprocess as sp
import shlex

PIPE = -1
STDOUT = -2
DEVNULL = -3

def run(cmd, **kwargs):
    '''
    runs the command through shlex if it's a string and sets
    universal_newlines to True (i.e. unicode streams). Passes additional
    key-word parameters to subprocess.run(). Returns a CompletedProcess
    object Refer to the official subprocess module documentation for
    more info.
    '''
    cmd = shlex.split(cmd) if isinstance(cmd, str) else cmd
    return sp.run(cmd, universal_newlines=True, **kwargs)


def Popen(cmd, **kwargs):
    '''
    Same as run(), but returns a Popen object.
    '''
    cmd = shlex.split(cmd) if isinstance(cmd, str) else cmd
    return sp.Popen(cmd, universal_newlines=True, **kwargs)


def grab(cmd, split=True, **kwargs):
    '''
    similar to the run() function, but returns the output of the
    command. By default, it returns the output as a list of lines (good
    for iterating). Use split=False to return a string. Doesn't catche errors
    by default. Use `check=True` to catch errors.
    '''
    out = run(cmd, stdout=PIPE, **kwargs).stdout
    if split:
        return out.splitlines()
    else:
        return out


def pipe(*args, split=True, input=None, stdin=None, stderr=None, **kwargs):
    '''
    like the grab() function, but will take a list of commands and pipe
    them into each other, one after another. If pressent, the 'stderr'
    parameter will be passed to all commands. 'input' and 'stdin' will
    be passed to the initial command all other **kwargs will be passed
    to the final command.
    '''
    out = grab(args[0], split=False, input=input, stdin=stdin, stderr=stderr)
    for cmd in args[1:-1]:
        out = grab(cmd, input=out, split=False, stderr=stderr)
    return grab(args[-1], split=split, input=out, stderr=stderr, **kwargs)
