"""PyInstaller runtime hook for Aqua Focus desktop builds."""

try:
    import pc_runtime_fixes  # noqa: F401
except Exception:
    pass

try:
    import pc_water_fixes  # noqa: F401
except Exception:
    pass
