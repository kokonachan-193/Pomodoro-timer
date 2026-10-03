"""Aqua Focus source-run runtime hook.

Python imports sitecustomize automatically when the project root is on sys.path.
Keep this file tiny: the actual patch lives in pc_runtime_fixes.py.
"""

try:
    import pc_runtime_fixes  # noqa: F401
except Exception:
    pass
