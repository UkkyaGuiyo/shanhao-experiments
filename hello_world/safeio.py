"""Read small regular files without following the final symlink or blocking on a FIFO."""
import os
import stat

def read_regular(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError("expected a bounded regular configuration file")
        with os.fdopen(fd, "rb", closefd=False) as source:
            data = source.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("configuration exceeds byte limit")
        return data
    finally:
        os.close(fd)
