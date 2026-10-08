"""Windows memory optimization utilities for WinKeySymb."""

import ctypes
from ctypes import wintypes
import gc

kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

kernel32.GetCurrentProcess.restype = wintypes.HANDLE
psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]


def trim_memory():
  """Force garbage collection and trim the process working set memory pages."""
  try:
    gc.collect()
    psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
  except Exception:
    pass
