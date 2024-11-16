# BIM Semantic Viewer

## Installation
- Use Python 3.12 or lower



## Coding

### Setup venv
> Note: some requirements are not in conda, it is better to use a Python venv and to install requirements with pip

Create virtual environment in the project root folder
```
python -m venv venv
```

Activate the venv

Linux:
```
source venv/bin/activate
```

Windows Powershell:
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\Activate.ps1
```

Install requirements
```
pip install -r requirements.txt
```

### Packaging
With activated venv:
```
pip install PyInstaller
```

To create a spec file, run with activated venv:
```
cd bimsemanticviewer
pyinstaller app.spec
```

Edit spec file: We need to add the IfcOpenSell IFC rules manually
```python
# -*- mode: python ; coding: utf-8 -*-

# Add these lines
import os
import glob
rules_path = "../venv/lib/python3.10/site-packages/ifcopenshell/express/rules" # Linux
# rules_path = "../venv/Lib/site-packages/ifcopenshell/express/rules" # Windows

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[(file, 'ifcopenshell/express/rules') for file in glob.glob(rules_path)], # Edit here
    hiddenimports=['ifcopenshell.express'], # Edit here
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='bimsemantic', # Edit here
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Set to False to hide console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='bimsemantic', # Edit here
)

```

Now run
```
pyinstaller app.spec
```


In case of any problems, try:
```
pip3 install --upgrade PyInstaller pyinstaller-hooks-contrib
```


### Translation
(Commands in the root directory of the project with venv enabled)

Update translations:
```
pyside6-lupdate bimsemantic/ui/*.py -ts bimsemantic/i18n/bimsemantic_de.ts
```

Edit the translations in QtLinguist and then release translation with:
```
pyside6-lrelease bimsemantic/i18n/bimsemantic_de.ts
```

### Todo
- Column Tag, Object Type, Description
- Quantities
- Selection? Copy Paste as table