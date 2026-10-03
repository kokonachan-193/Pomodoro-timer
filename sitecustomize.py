"""Aqua Focus source-run runtime hook.

Python imports sitecustomize automatically when the project root is on sys.path.
Keep this file tiny: the actual desktop patches live in pc_runtime_fixes.py and
pc_water_fixes.py.
"""

try:
    import pc_runtime_fixes  # noqa: F401
except Exception:
    pass

try:
    import pc_water_fixes  # noqa: F401
except Exception:
    pass
