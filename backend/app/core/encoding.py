import sys
import io
import os
import logging

_initialized = False

def setup_utf8_environment():
    """
    Centralized UTF-8 environment and stream configuration.
    Ensures safe handling of Unicode chemical formulas (e.g. CO₂, SO₂, H₂O, O₂, NaOH,
    Greek letters, degree symbols °C, subscripts/superscripts) across all Windows
    consoles, child processes, logging handlers, and standard I/O streams.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    # 1. Environment variables for child processes, workers, and subprocesses
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    # 2. Reconfigure stdout and stderr on Windows
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None:
            try:
                if hasattr(stream, "reconfigure"):
                    stream.reconfigure(encoding="utf-8", errors="replace")
                elif hasattr(stream, "buffer"):
                    setattr(
                        sys,
                        stream_name,
                        io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace")
                    )
            except Exception:
                pass

    # 3. Ensure Python logging handlers use UTF-8 streams
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            try:
                if hasattr(handler.stream, "reconfigure"):
                    handler.stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_builtin_print = print

def safe_print(*args, **kwargs):
    """
    Safely print to stdout without throwing UnicodeEncodeError on any console.
    Attempts direct UTF-8 write first; if a charmap or legacy encoding error occurs,
    encodes gracefully with replacement rather than raising an unhandled exception.
    """
    try:
        _builtin_print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            clean_args = [
                str(arg).encode(encoding, errors="replace").decode(encoding, errors="replace")
                for arg in args
            ]
            _builtin_print(*clean_args, **kwargs)
        except Exception:
            pass
    except Exception:
        pass


# Run setup immediately upon import
setup_utf8_environment()
