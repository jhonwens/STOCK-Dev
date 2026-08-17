#!/usr/bin/env python3
"""列出 PyInstaller PYZ 中所有模块"""
import sys
# In frozen mode, we can list modules from the archive
import pyimod02_importers  # noqa - PyInstaller internal

# List all frozen modules
print("Frozen modules in PYZ:")
try:
    # PyInstaller stores module list in sys._MEIPASS
    import os
    # Walk the frozen importer
    for imp in sys.meta_path:
        name = getattr(imp, '__name__', type(imp).__name__)
        if 'PyInstaller' in name or 'Frozen' in name:
            toc = getattr(imp, 'toc', None)
            if toc:
                for modname in toc:
                    if 'backend' in modname:
                        print(f"  {modname}")
except Exception as e:
    print(f"  Error: {e}")

# Alternative: just try to list from sys.modules after imports
# Show all that have 'backend' in name
print("\nbackend.* in sys.modules when discovered:")
for m in sorted(sys.modules.keys()):
    if m.startswith('backend'):
        print(f"  {m} -> {getattr(sys.modules[m], '__file__', sys.modules[m])}")