"""Shared bounded subprocess I/O and process-tree containment.

The validation control plane uses this module for existing Git probes and its
single pytest child.  It never buffers unbounded pipe output and never treats
parent exit as proof that descendants have exited.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import errno
import os
import signal
import subprocess
import tempfile
import threading
import time
from typing import Callable, Mapping, Sequence


class ProcessErrorReason(str, Enum):
    START_FAILED = "start_failed"
    CONTAINMENT_FAILED = "containment_failed"
    OUTPUT_LIMIT = "output_limit"
    TIMEOUT = "timeout"
    PIPE_READ_FAILED = "pipe_read_failed"
    OBSERVATION_FAILED = "observation_failed"
    TERMINATION_FAILED = "termination_failed"


class StreamName(str, Enum):
    STDOUT = "stdout"
    STDERR = "stderr"


@dataclass(frozen=True)
class BoundedProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    wall_ns: int
    termination_confirmed: bool
    peak_rss_bytes: int | None = None


class ProcessControlError(RuntimeError):
    def __init__(
        self,
        reason: ProcessErrorReason,
        message: str,
        *,
        stream: StreamName | None = None,
        stdout: bytes = b"",
        stderr: bytes = b"",
        termination_confirmed: bool = False,
        peak_rss_bytes: int | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.stream = stream
        self.stdout = stdout
        self.stderr = stderr
        self.termination_confirmed = termination_confirmed
        self.peak_rss_bytes = peak_rss_bytes


def process_tree_popen_kwargs(
    *, platform_name: str | None = None
) -> dict[str, object]:
    """Return Popen flags that create a separately addressable process tree."""
    selected = os.name if platform_name is None else platform_name
    if selected == "nt":
        return {
            "creationflags": (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
            )
        }
    return {"start_new_session": True}


class _ProcessTreeGuard:
    def terminate_and_confirm(
        self, process: subprocess.Popen[bytes], timeout_seconds: float
    ) -> bool:
        raise NotImplementedError


class _PosixProcessTreeGuard(_ProcessTreeGuard):
    def __init__(self, pgid: int) -> None:
        self._pgid = pgid
        self._closed = False

    def _group_exists(self) -> bool:
        try:
            os.killpg(self._pgid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def terminate_and_confirm(
        self, process: subprocess.Popen[bytes], timeout_seconds: float
    ) -> bool:
        if self._closed:
            return True
        try:
            if self._group_exists():
                os.killpg(self._pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            return False
        deadline = time.monotonic() + timeout_seconds
        try:
            remaining = max(0.0, deadline - time.monotonic())
            process.wait(timeout=remaining)
        except (subprocess.TimeoutExpired, OSError):
            return False
        while self._group_exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self._closed = not self._group_exists()
        return self._closed


class _WindowsProcessTreeGuard(_ProcessTreeGuard):
    def __init__(self, process: subprocess.Popen[bytes]) -> None:
        import ctypes
        from ctypes import wintypes

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD),
                ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD),
                ("TotalTerminatedProcesses", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        )
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = (
            wintypes.HANDLE,
            wintypes.HANDLE,
        )
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.QueryInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        )
        kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
        ntdll.NtResumeProcess.argtypes = (wintypes.HANDLE,)
        ntdll.NtResumeProcess.restype = ctypes.c_long

        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
        self._ctypes = ctypes
        self._kernel32 = kernel32
        self._accounting_type = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION
        self._job = job
        self._closed = False
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        limits.BasicLimitInformation.LimitFlags = 0x00002000
        if not kernel32.SetInformationJobObject(
            job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(job)
            self._closed = True
            raise OSError(error, "SetInformationJobObject failed")
        process_handle = wintypes.HANDLE(int(process._handle))
        if not kernel32.AssignProcessToJobObject(job, process_handle):
            error = ctypes.get_last_error()
            kernel32.CloseHandle(job)
            self._closed = True
            raise OSError(error, "AssignProcessToJobObject failed")
        resume_status = int(ntdll.NtResumeProcess(process_handle))
        if resume_status < 0:
            kernel32.TerminateJobObject(job, 1)
            kernel32.CloseHandle(job)
            self._closed = True
            raise OSError(resume_status, "NtResumeProcess failed")

    def _active_processes(self) -> int:
        value = self._accounting_type()
        if not self._kernel32.QueryInformationJobObject(
            self._job,
            1,
            self._ctypes.byref(value),
            self._ctypes.sizeof(value),
            None,
        ):
            raise OSError(
                self._ctypes.get_last_error(),
                "QueryInformationJobObject failed",
            )
        return int(value.ActiveProcesses)

    def _close(self) -> bool:
        if self._closed:
            return True
        result = bool(self._kernel32.CloseHandle(self._job))
        self._closed = True
        return result

    def terminate_and_confirm(
        self, process: subprocess.Popen[bytes], timeout_seconds: float
    ) -> bool:
        if self._closed:
            return True
        deadline = time.monotonic() + timeout_seconds
        try:
            active = self._active_processes()
            if active and not self._kernel32.TerminateJobObject(self._job, 1):
                return False
            while self._active_processes() and time.monotonic() < deadline:
                time.sleep(0.01)
            if self._active_processes():
                return False
            try:
                remaining = max(0.0, deadline - time.monotonic())
                process.wait(timeout=remaining)
            except (subprocess.TimeoutExpired, OSError):
                return False
            return self._close()
        except OSError:
            self._close()
            return False


def prepare_process_tree(
    process: subprocess.Popen[bytes],
    *,
    platform_name: str | None = None,
) -> _ProcessTreeGuard:
    """Establish containment immediately or kill the uncontained child."""
    selected = os.name if platform_name is None else platform_name
    try:
        if selected == "nt":
            return _WindowsProcessTreeGuard(process)
        pgid = os.getpgid(process.pid)
        if pgid != process.pid:
            raise OSError("child did not establish a new process group")
        return _PosixProcessTreeGuard(pgid)
    except BaseException as exc:
        try:
            process.kill()
            process.wait(timeout=5)
        except BaseException:
            pass
        raise ProcessControlError(
            ProcessErrorReason.CONTAINMENT_FAILED,
            "cannot establish subprocess tree containment",
            termination_confirmed=process.poll() is not None,
        ) from exc


def terminate_process_tree(
    process: subprocess.Popen[bytes] | object,
    *,
    guard: _ProcessTreeGuard | None = None,
    platform_name: str | None = None,
    timeout_seconds: float = 5.0,
) -> bool:
    """Terminate and confirm the complete owned tree."""
    if guard is not None:
        return guard.terminate_and_confirm(process, timeout_seconds)  # type: ignore[arg-type]
    selected = os.name if platform_name is None else platform_name
    pid = getattr(process, "pid", None)
    if selected != "nt" and type(pid) is int and pid > 0:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            return False
    elif selected == "nt" and type(pid) is int and pid > 0:
        try:
            completed = subprocess.run(
                ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=timeout_seconds,
                shell=False,
            )
            if completed.returncode != 0 and getattr(process, "poll")() is None:
                return False
        except (OSError, subprocess.TimeoutExpired):
            if getattr(process, "poll")() is None:
                return False
    killer = getattr(process, "kill", None)
    if callable(killer):
        try:
            killer()
        except OSError:
            pass
    waiter = getattr(process, "wait", None)
    if callable(waiter):
        try:
            waiter(timeout=timeout_seconds)
        except BaseException:
            return False
    try:
        return getattr(process, "poll")() is not None
    except BaseException:
        return False


_MAX_STAGED_INPUT_BYTES = 64 * 1024 * 1024


def _drain_pipe(
    pipe: object,
    *,
    maximum: int,
    combined_maximum: int | None,
    combined_size: list[int],
    stream: StreamName,
    storage: bytearray,
    exceeded: list[StreamName],
    failures: list[BaseException],
    completed: list[StreamName],
    state_lock: threading.Lock,
    signal_event: threading.Event,
) -> None:
    try:
        reader = getattr(pipe, "read1", None)
        if not callable(reader):
            reader = getattr(pipe, "read")
        while True:
            chunk = reader(64 * 1024)
            if not chunk:
                return
            if type(chunk) is not bytes:
                raise TypeError("subprocess pipe returned non-bytes")
            with state_lock:
                stream_remaining = max(0, maximum - len(storage))
                combined_remaining = (
                    stream_remaining
                    if combined_maximum is None
                    else max(0, combined_maximum - combined_size[0])
                )
                retained = min(len(chunk), stream_remaining, combined_remaining)
                if retained:
                    storage.extend(chunk[:retained])
                    combined_size[0] += retained
                if retained != len(chunk):
                    exceeded.append(stream)
                    signal_event.set()
                    return
    except BaseException as exc:
        with state_lock:
            failures.append(exc)
    finally:
        with state_lock:
            completed.append(stream)
        signal_event.set()


def capture_bounded_process(
    command: Sequence[str],
    *,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
    timeout_seconds: float,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    input_bytes: bytes | None = None,
    max_combined_output_bytes: int | None = None,
    rss_reader_factory: (
        Callable[[subprocess.Popen[bytes]], Callable[[], int | None]] | None
    ) = None,
) -> BoundedProcessResult:
    """Run one contained process with hard input, output and time bounds."""
    if (
        not command
        or any(type(item) is not str or not item for item in command)
        or type(max_stdout_bytes) is not int
        or max_stdout_bytes < 0
        or type(max_stderr_bytes) is not int
        or max_stderr_bytes < 0
        or not isinstance(timeout_seconds, (int, float))
        or isinstance(timeout_seconds, bool)
        or timeout_seconds <= 0
        or (input_bytes is not None and type(input_bytes) is not bytes)
        or (
            input_bytes is not None
            and len(input_bytes) > _MAX_STAGED_INPUT_BYTES
        )
        or (
            max_combined_output_bytes is not None
            and (
                type(max_combined_output_bytes) is not int
                or max_combined_output_bytes < 0
            )
        )
        or (rss_reader_factory is not None and not callable(rss_reader_factory))
    ):
        raise ValueError("bounded process arguments are invalid")

    staged_input = None
    if input_bytes is not None:
        try:
            staged_input = tempfile.TemporaryFile()
            staged_input.write(input_bytes)
            staged_input.flush()
            staged_input.seek(0)
        except OSError as exc:
            if staged_input is not None:
                staged_input.close()
            raise ProcessControlError(
                ProcessErrorReason.START_FAILED,
                "cannot stage bounded subprocess input",
            ) from exc

    started = time.monotonic_ns()
    try:
        try:
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                env=None if env is None else dict(env),
                stdin=(subprocess.DEVNULL if staged_input is None else staged_input),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                **process_tree_popen_kwargs(),
            )
        except OSError as exc:
            raise ProcessControlError(
                ProcessErrorReason.START_FAILED,
                "cannot start bounded subprocess",
            ) from exc
    finally:
        if staged_input is not None:
            staged_input.close()

    guard: _ProcessTreeGuard | None = None
    threads: tuple[threading.Thread, ...] = ()
    started_threads: list[threading.Thread] = []
    termination_confirmed = False
    stdout = bytearray()
    stderr = bytearray()
    exceeded: list[StreamName] = []
    failures: list[BaseException] = []
    completed_streams: list[StreamName] = []
    combined_size = [0]
    state_lock = threading.Lock()
    signal_event = threading.Event()
    reason: ProcessErrorReason | None = None
    peak_rss_bytes: int | None = None
    try:
        guard = prepare_process_tree(process)
        assert process.stdout is not None
        assert process.stderr is not None
        threads = (
            threading.Thread(
                target=_drain_pipe,
                kwargs={
                    "pipe": process.stdout,
                    "maximum": max_stdout_bytes,
                    "combined_maximum": max_combined_output_bytes,
                    "combined_size": combined_size,
                    "stream": StreamName.STDOUT,
                    "storage": stdout,
                    "exceeded": exceeded,
                    "failures": failures,
                    "completed": completed_streams,
                    "state_lock": state_lock,
                    "signal_event": signal_event,
                },
                daemon=True,
            ),
            threading.Thread(
                target=_drain_pipe,
                kwargs={
                    "pipe": process.stderr,
                    "maximum": max_stderr_bytes,
                    "combined_maximum": max_combined_output_bytes,
                    "combined_size": combined_size,
                    "stream": StreamName.STDERR,
                    "storage": stderr,
                    "exceeded": exceeded,
                    "failures": failures,
                    "completed": completed_streams,
                    "state_lock": state_lock,
                    "signal_event": signal_event,
                },
                daemon=True,
            ),
        )
        for thread in threads:
            thread.start()
            started_threads.append(thread)

        rss_reader = (
            None if rss_reader_factory is None else rss_reader_factory(process)
        )
        if rss_reader is not None and not callable(rss_reader):
            raise TypeError("RSS reader factory returned a non-callable")
        deadline = time.monotonic() + float(timeout_seconds)
        while True:
            with state_lock:
                has_exceeded = bool(exceeded)
                has_failures = bool(failures)
            if has_exceeded:
                reason = ProcessErrorReason.OUTPUT_LIMIT
                break
            if has_failures:
                reason = ProcessErrorReason.PIPE_READ_FAILED
                break
            if process.poll() is not None:
                break
            if rss_reader is not None:
                try:
                    sample = rss_reader()
                except BaseException as exc:
                    failures.append(exc)
                    reason = ProcessErrorReason.OBSERVATION_FAILED
                    break
                if sample is not None:
                    if type(sample) is not int or sample < 0:
                        reason = ProcessErrorReason.OBSERVATION_FAILED
                        break
                    peak_rss_bytes = (
                        sample
                        if peak_rss_bytes is None
                        else max(peak_rss_bytes, sample)
                    )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = ProcessErrorReason.TIMEOUT
                break
            signal_event.wait(timeout=min(0.01, remaining))
            signal_event.clear()
    except (KeyboardInterrupt, SystemExit):
        raise
    except ProcessControlError:
        raise
    except BaseException as exc:
        failures.append(exc)
        reason = ProcessErrorReason.PIPE_READ_FAILED
    finally:
        termination_confirmed = terminate_process_tree(process, guard=guard)
        for thread in started_threads:
            thread.join(timeout=1)
        if any(thread.is_alive() for thread in started_threads):
            failures.append(RuntimeError("subprocess pipe reader did not stop"))
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass

    bounded_stdout = bytes(stdout)
    bounded_stderr = bytes(stderr)
    wall_ns = max(0, time.monotonic_ns() - started)
    if not termination_confirmed:
        raise ProcessControlError(
            ProcessErrorReason.TERMINATION_FAILED,
            "subprocess tree termination could not be confirmed",
            stdout=bounded_stdout,
            stderr=bounded_stderr,
            termination_confirmed=False,
            peak_rss_bytes=peak_rss_bytes,
        )
    if reason is None and failures:
        reason = ProcessErrorReason.PIPE_READ_FAILED
    if reason is None and exceeded:
        reason = ProcessErrorReason.OUTPUT_LIMIT
    if reason is not None:
        stream = exceeded[0] if exceeded else None
        raise ProcessControlError(
            reason,
            f"bounded subprocess failed: {reason.value}",
            stream=stream,
            stdout=bounded_stdout,
            stderr=bounded_stderr,
            termination_confirmed=True,
            peak_rss_bytes=peak_rss_bytes,
        )
    if process.returncode is None:
        raise ProcessControlError(
            ProcessErrorReason.TERMINATION_FAILED,
            "subprocess return code is unavailable after termination",
            stdout=bounded_stdout,
            stderr=bounded_stderr,
            termination_confirmed=True,
            peak_rss_bytes=peak_rss_bytes,
        )
    return BoundedProcessResult(
        returncode=int(process.returncode),
        stdout=bounded_stdout,
        stderr=bounded_stderr,
        wall_ns=wall_ns,
        termination_confirmed=True,
        peak_rss_bytes=peak_rss_bytes,
    )