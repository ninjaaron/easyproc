# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import subprocess as sp
import shlex
import functools
import signal
from typing import Union, Sequence, Collection, Tuple, IO
from numbers import Number

StrOrSeq = Union[str, Sequence[str]]
IOorFD = Union[IO, int]


class reify:
    """"stolen" from Pylons"""

    def __init__(self, wrapped):
        self.wrapped = wrapped
        functools.update_wrapper(self, wrapped)

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self
        val = self.wrapped(inst)
        setattr(inst, self.wrapped.__name__, val)
        return val


def Popen(
    cmd: StrOrSeq,
    input: StrOrSeq = None,
    stdin: IOorFD = None,
    bytes: bool = False,
    shell: bool = False,
    **kwargs,
):
    if input is not None:
        if stdin is not None:
            raise ValueError("stdin and input arguments may not both be used.")
        stdin = PIPE
    elif isinstance(stdin, ProcStream):
        stdin = stdin.stream

    if isinstance(cmd, str) and not shell:
        cmd = shlex.split(cmd)

    proc = sp.Popen(
        cmd, stdin=stdin, universal_newlines=not bytes, shell=shell, **kwargs
    )
    if input:
        if proc.stdin is None:
            raise ValueError(
                "stdin should not be None if input was used. "
                "this branch should not be reached"
            )
        elif isinstance(input, str):
            proc._stdin_write(input)  # type: ignore
        else:
            for i in input:
                proc.stdin.writelines(i)
                proc.stdin.close()
    return proc


ALL = -1


def mkchecker(
    cmd: StrOrSeq,
    proc: sp.Popen,
    ok_codes: Union[int, Collection[int]] = 0,
    check: bool = True,
):
    _ok_codes = set()
    if isinstance(ok_codes, int):
        _ok_codes.add(ok_codes)
    elif ok_codes == ALL:
        check = False
    else:
        for code in ok_codes:
            if isinstance(code, int):
                _ok_codes.add(code)
            else:
                _ok_codes.update(code)

    def check_code() -> int:
        retcode = proc.wait()
        if check and retcode not in _ok_codes:
            raise CalledProcessError(
                retcode, cmd, output=proc.stdout, stderr=proc.stderr
            )
        return retcode

    return check_code


class ProcStream:
    def __init__(
        self,
        cmd: StrOrSeq,
        proc: sp.Popen = None,
        ok_codes: Union[int, Collection[int]] = 0,
        check: bool = True,
        **kwargs,
    ):
        self.cmd = cmd
        self.kwargs = kwargs
        self.ok_codes = ok_codes
        self.check = check
        if isinstance(proc, sp.Popen):
            self.proc = proc
        elif proc is not None:
            raise TypeError("'proc' must be a subprocess.Popen instance.")

    @reify
    def proc(self):
        return Popen(self.cmd, stdout=PIPE, **self.kwargs)

    @reify
    def stream(self):
        return self.proc.stdout

    def __enter__(self):
        self.check_code = mkchecker(self.cmd, self.proc, self.ok_codes, self.check)
        return self

    def __exit__(self, type, value, traceback):
        self.stream.close()
        self.check_code()

    def __getattr__(self, name):
        try:
            return getattr(self.stream, name)
        except AttributeError as e:
            try:
                return getattr(self.proc, name)
            except AttributeError:
                raise e

    def __iter__(self):
        with self:
            yield from (i.rstrip("\n") for i in self.stream)

    def __repr__(self):
        name = self.__class__.__name__
        return "<{} {!r}>".format(name, self.cmd)

    def __str__(self):
        with self:
            _str = self.read()
            if _str[-1] == "\n":
                return _str[:-1]
            return _str

    def splitlines(self):
        with self:
            return self.read().splitlines()


class ProcErr(ProcStream):
    @reify
    def proc(self):
        return Popen(self.cmd, stderr=PIPE, **self.kwargs)

    @reify
    def stream(self):
        return self.proc.stderr


class CompletedProcess:
    """A process that has finished running.

    This is returned by run(). The distinction between this and the form found
    in the subprocess module is that stdin and stderr are ProcStream instances,
    rather than byte-strings.

    Attributes:
      args: The list or str args passed to run().
      returncode: The exit code of the process, negative for signals.
      stdout: The standard output (None if not captured).
      stderr: The standard error (None if not captured).
    """

    def __init__(
        self,
        args: Sequence[str],
        returncode: int,
        stdout: ProcStream = None,
        stderr: ProcErr = None,
    ):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        args = [
            "args={!r}".format(self.args),
            "returncode={!r}".format(self.returncode),
        ]
        if self.stdout is not None:
            args.append("stdout={!r}".format(self.stdout.str))
        if self.stderr is not None:
            args.append("stderr={!r}".format(self.stderr.str))
        return "{}({})".format(type(self).__name__, ", ".join(args))

    def check_returncode(self):
        """Raise CalledProcessError if the exit code is non-zero."""
        if self.returncode:
            raise CalledProcessError(
                self.returncode, self.args, self.stdout.stream, self.stderr.stream
            )


# this was originally subprocess.run from 3.5. Now... it's different...
def run(
    cmd: StrOrSeq,
    ok_codes: Union[int, Collection[int]] = 0,
    timeout: Number = None,
    check: bool = True,
    stdout: Union[IOorFD] = None,
    stderr: Union[IOorFD] = None,
    **kwargs,
):
    """A clone of subprocess.run with a few small differences:

        - unicode streams enabled by default.
        - shlex.split() run on cmd if it is a string and shell=False
        - check is True by default (raises exception on error)
        - stdout and stderr attributes of output are ProcOutput instances,
          rather than regular strings (or byte-strings).

    As with subprocess.run, a string may be piped to the command's stdin via
    the input arguments, and  all other kwargs are passed to Popen.
    The "timeout" option is not supported on Python 2.
    """
    proc = Popen(cmd, stdout=stdout, stderr=stderr, **kwargs)
    stdout_ = ProcStream(cmd, proc=proc, ok_codes=ok_codes, check=check)
    stderr_ = ProcErr(cmd, proc=proc, ok_codes=ok_codes, check=check)
    if timeout:
        try:
            proc.wait(timeout=timeout)
        except TimeoutExpired:
            proc.kill()
            raise TimeoutExpired(cmd, timeout, output=proc.stdout, stderr=proc.stderr)
        except:
            proc.kill()
            proc.wait()
            raise
    if check and ok_codes != ALL:
        retcode = mkchecker(cmd, proc, ok_codes)()
    else:
        retcode = proc.poll()
    return CompletedProcess(cmd, retcode, stdout_, stderr_)


def grab(
    cmd: StrOrSeq,
    ok_codes: Union[int, Collection[int]] = 0,
    stream: IOorFD = 1,
    **kwargs,
):
    """takes all the same arguments as run(), but captures stdout and returns
    only that. Very practical for iterating on command output other immediate
    uses.

    If both=True, stderr will captured *in the same stream* as stdout (like
    2>&1 at the command line). For access to both streams separately, use run()
    or Popen and read the subprocess docs.
    """
    args = {"cmd": cmd, "ok_codes": ok_codes}
    kwargs.update(args)
    if stream == 1 + 2:
        return ProcStream(stderr=STDOUT, **kwargs)
    elif stream == 2:
        return ProcErr(**kwargs)
    elif stream == 1:
        return ProcStream(**kwargs)
    else:
        raise ValueError(
            "Valid stream values are 1 (stdout), 2 (stderr) and 3 (both together). "
            "got %s." % stream
        )


def grab2(
    cmd: StrOrSeq, ok_codes: Union[int, Collection[int]] = 0, check=True, **kwargs
):
    proc = Popen("cmd", stdout=PIPE, stderr=PIPE, **kwargs)
    return (ProcStream(cmd, proc, ok_codes, check), ProcErr(cmd, proc, ok_codes, check))


def pipe(
    *commands: StrOrSeq,
    grab_it: bool = False,
    input: StrOrSeq = None,
    stdin: IOorFD = None,
    stderr: IOorFD = None,
    **kwargs,
):
    """like the run() function, but will take a list of commands and pipe them
    into each other, one after another. If pressent, the 'stderr' parameter
    will be passed to all commands. Either 'input' or 'stdin' will be passed to
    the initial command all other **kwargs will be passed to the final command.

    If grab_it=True, stdout will be returned as a ProcOutput instance.
    """
    out = Popen(
        commands[0], input=input, stdin=stdin, stdout=PIPE, stderr=stderr
    ).stdout
    for cmd in commands[1:-1]:
        out = Popen(cmd, stdin=out, stdout=PIPE, stderr=stderr).stdout
    if grab_it:
        return grab(commands[-1], stdin=out, stderr=stderr, **kwargs)
    else:
        return run(commands[-1], stdin=out, stderr=stderr, **kwargs)


# all code after this point is taken directly from the subprocess module
# (mostly-ish) just to complete the subprocess.run interface...
PIPE = -1
STDOUT = -2
DEVNULL = -3


class SubprocessError(Exception):
    pass


class CalledProcessError(SubprocessError):
    """Raised when a check_call() or check_output() process returns non-zero.

    The exit status will be stored in the returncode attribute, negative
    if it represents a signal number.

    check_output() will also store the output in the output attribute.
    """

    def __init__(
        self, returncode: int, cmd: StrOrSeq, output: IO = None, stderr: IO = None
    ):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                return "Command '%s' died with %r." % (
                    self.cmd,
                    signal.Signals(-self.returncode),
                )
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (
                    self.cmd,
                    -self.returncode,
                )
        else:
            return "Command '%s' returned non-zero exit status %d." % (
                self.cmd,
                self.returncode,
            )

    @reify
    def stdout(self):
        """Alias for output attribute, to match stderr"""
        return self.output


class TimeoutExpired(SubprocessError):
    """This exception is raised when the timeout expires while waiting for a
    child process.
    """

    def __init__(
        self, cmd: StrOrSeq, timeout: Number, output: IO = None, stderr: IO = None,
    ):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output
        self.stderr = stderr

    def __str__(self):
        return "Command '%s' timed out after %s seconds" % (self.cmd, self.timeout)

    @reify
    def stdout(self):
        return self.output
