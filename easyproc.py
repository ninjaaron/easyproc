import subprocess as sp
import shlex
import six


class ProcOutput(str):
    """subclass of str designed for handling command output.

    ProcOutput acts like a string in most cases, but acts like a tuple of lines
    for most sequence operations. (except it keeps str.count)
    """
    # I don't dare overried str's __init__ method, so I use this property to
    # initialize a value.
    @property
    def tuple(self):
        try:
            return self._tpl
        except AttributeError:
            self._tpl = tuple(self.splitlines())
            return self._tpl

    def __iter__(self):
        return iter(self.tuple)

    def __repr__(self):
        return "ProcOutput('%s')" % self

    def __getitem__(self, index):
        return self.tuple[index]

    def __len__(self):
        return len(self.tuple)

    def __reversed__(self):
        return reversed(self.tuple)

        if isinstance(other, ProcOutput):
            return ProcOutput(str(self) + other)

        elif isinstance(other, tuple):
            return self.tuple + other
        else:
            return str(self) + other

    def index(self, value):
        """return first index of value. Raises ValueError if The
        value is not present.
        """
        return self.tuple.index(value)


class CompletedProcess(object):
    """A process that has finished running.

    This is returned by run(). The distinction between this and the form found
    in the subprocess module is that stdin and stderr are ProcOutput instances,
    rather than byte-strings.

    Attributes:
      args: The list or str args passed to run().
      returncode: The exit code of the process, negative for signals.
      stdout: The standard output (None if not captured).
      stderr: The standard error (None if not captured).
    """
    def __init__(self, args, returncode, stdout=None, stderr=None):
        self.args = args
        self.returncode = returncode
        self.stdout = ProcOutput(stdout) if stdout else stdout
        self.stderr = ProcOutput(stderr) if stderr else stderr

    def __repr__(self):
        args = ['args={!r}'.format(self.args),
                'returncode={!r}'.format(self.returncode)]
        if self.stdout is not None:
            args.append('stdout={!r}'.format(self.stdout))
        if self.stderr is not None:
            args.append('stderr={!r}'.format(self.stderr))
        return "{}({})".format(type(self).__name__, ', '.join(args))

    def check_returncode(self):
        """Raise CalledProcessError if the exit code is non-zero."""
        if self.returncode:
            raise CalledProcessError(self.returncode, self.args, self.stdout,
                                     self.stderr)


def Popen(cmd, universal_newlines=True, shell=False, **kwargs):
    """All args are passed directly to subprocess.Popen except cmd. If cmd is a
    string and shell=False (default), it will be sent through shlex.split prior
    to being sent to subprocess.Popen as *args.

    The only other difference is that this defualts universal_newlines to True
    (unicode streams).
    """
    if isinstance(cmd, str) and shell == False:
        cmd = shlex.split(cmd)
    return sp.Popen(cmd, universal_newlines=universal_newlines,
                    shell=shell, **kwargs)


# this is only very slightly modifided from subprocess.run in 3.5
def run(cmd, input=None, timeout=None, check=True, **kwargs):
    """A clone of subprocess.run with a few small differences:

        - universal_newlines enabled by default (unicode streams)
        - shlex.split() run on cmd if it is a string and shell=False
        - check is True by default (raises exception on error)
        - stdout and stderr attributes of output are ProcOutput instances,
          rather than regular strings (or byte-strings).


    As with subprocess.run, a string may be piped to the command's stdin via
    the input arguments, and  all other kwargs are passed to Popen.
    The "timeout" option is not supported on Python 2.
    """
    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = PIPE

    proc = Popen(cmd, **kwargs)
    if six.PY2:
        stdout, stderr = proc.communicate(input)
    else:
        try:
            stdout, stderr = proc.communicate(input, timeout=timeout)
        except sp.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise TimeoutExpired(proc.args, timeout, output=stdout,
                                 stderr=stderr)
        except:
            proc.kill()
            proc.wait()
            raise
    retcode = proc.poll()
    if check and retcode:
        raise CalledProcessError(retcode, cmd,
                                 output=stdout, stderr=stderr)
    return CompletedProcess(cmd, retcode, stdout, stderr)


def grab(cmd, both=False, **kwargs):
    """takes all the same arguments as run(), but captures stdout and returns
    only that. Very practical for iterating on command output other immediate
    uses.

    If both=True, stderr will captured *in the same stream* as stdout (like
    2>&1 at the command line). For access to both streams separately, use run()
    or Popen and read the subprocess docs.
    """
    if both:
        return run(cmd, stdout=PIPE, stderr=STDIN, **kwargs).stdout
    else:
        return run(cmd, stdout=PIPE, **kwargs).stdout


def pipe(*args, input=None, stdin=None, stderr=None, **kwargs):
    '''
    like the grab() function, but will take a list of commands and pipe
    them into each other, one after another. If pressent, the 'stderr'
    parameter will be passed to all commands. 'input' and 'stdin' will
    be passed to the initial command all other **kwargs will be passed
    to the final command.
    '''
    out = grab(args[0], input=input, stdin=stdin, stderr=stderr)
    for cmd in args[1:-1]:
        out = grab(cmd, input=out, stderr=stderr)
    return grab(args[-1], input=out, stderr=stderr, **kwargs)


# all code after this point is taken directly from the subprocess module, just
# to get the subprocess.run interface.

PIPE = -1
STDOUT = -2
DEVNULL = -3


class SubprocessError(Exception): pass


class CalledProcessError(SubprocessError):
    """Raised when a check_call() or check_output() process returns non-zero.

    The exit status will be stored in the returncode attribute, negative
    if it represents a signal number.

    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                return "Command '%s' died with %r." % (
                        self.cmd, signal.Signals(-self.returncode))
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (
                        self.cmd, -self.returncode)
        else:
            return "Command '%s' returned non-zero exit status %d." % (
                    self.cmd, self.returncode)

    @property
    def stdout(self):
        """Alias for output attribute, to match stderr"""
        return self.output

    @stdout.setter
    def stdout(self, value):
        # There's no obvious reason to set this, but allow it anyway so
        # .stdout is a transparent alias for .output
        self.output = value


class TimeoutExpired(SubprocessError):
    """This exception is raised when the timeout expires while waiting for a
    child process.
    """
    def __init__(self, cmd, timeout, output=None, stderr=None):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output
        self.stderr = stderr

    def __str__(self):
        return ("Command '%s' timed out after %s seconds" %
                (self.cmd, self.timeout))

    @property
    def stdout(self):
        return self.output

    @stdout.setter
    def stdout(self, value):
        # There's no obvious reason to set this, but allow it anyway so
        # .stdout is a transparent alias for .output
        self.output = value
