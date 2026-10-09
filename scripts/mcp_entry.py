"""Relocatable stdio launchers for Python MCP packages."""
import importlib
import os
from pathlib import Path
os.environ['PATH'] = str(Path(__file__).resolve().parent / 'media') + os.pathsep + os.environ.get('PATH', '')
import inspect
import asyncio
import sys
ALLOWED={"screenview_mcp.server:main","inputcontrol_mcp.server:main","transcripcion_mcp.server:main"}
if len(sys.argv)<2 or sys.argv[1] not in ALLOWED:raise SystemExit("Unknown MCP entry point")
module,function=sys.argv[1].split(":")
entry=getattr(importlib.import_module(module),function)
sys.argv=[module,*sys.argv[2:]]
result=entry()
if inspect.isawaitable(result):asyncio.run(result)
