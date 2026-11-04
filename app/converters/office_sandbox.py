"""Launch LibreOffice with access to runtime files and one job's files only."""

import ctypes
import errno
import os
import socket
import sys
from pathlib import Path


class ArgumentComparison(ctypes.Structure):
    _fields_ = [
        ("arg", ctypes.c_uint),
        ("op", ctypes.c_uint),
        ("value", ctypes.c_uint64),
        ("unused", ctypes.c_uint64),
    ]


def restrict_sockets():
    lib = ctypes.CDLL("libseccomp.so.2")
    lib.seccomp_init.restype = ctypes.c_void_p
    ctx = ctypes.c_void_p(lib.seccomp_init(0x7FFF0000))  # SCMP_ACT_ALLOW
    if not ctx:
        raise RuntimeError("Cannot initialize seccomp")
    try:
        rule = ArgumentComparison(0, 1, socket.AF_UNIX, 0)  # SCMP_CMP_NE
        syscall = lib.seccomp_syscall_resolve_name(b"socket")
        if (
            syscall < 0
            or lib.seccomp_rule_add_array(
                ctx, 0x00050000 | errno.EPERM, syscall, 1, ctypes.byref(rule)
            )
            != 0
        ):
            raise RuntimeError("Cannot restrict sockets")
        if lib.seccomp_load(ctx) != 0:
            raise RuntimeError("Cannot install seccomp filter")
    finally:
        lib.seccomp_release(ctx)


def main():
    source, output, profile, *command = sys.argv[1:]
    read = "read-file,read-dir"
    write = (
        read
        + ",write-file,truncate,remove-file,remove-dir,make-dir,make-reg,make-sock,make-fifo,make-sym,refer"
    )
    args = [
        "setpriv",
        "--no-new-privs",
        "--landlock-access",
        "fs:" + write + ",execute,make-char,make-block",
    ]

    def allow(path, access):
        if Path(path).exists():
            args.extend(["--landlock-rule", f"path-beneath:{access}:{path}"])

    for path in ("/usr", "/etc", "/var/cache/fontconfig", "/dev"):
        allow(path, read + (",execute" if path == "/usr" else ""))
    for path in ("/dev/null", "/dev/zero"):
        allow(path, "read-file,write-file")
    allow("/tmp", write)

    allow("/dev/shm", write)
    allow(Path(source).parent, write)
    allow(source, "read-file")
    allow(output, write)
    allow(profile, write)
    restrict_sockets()
    os.execvp(args[0], args + ["--", *command])


if __name__ == "__main__":
    main()
