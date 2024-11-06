# BIM Semantic Viewer

## Installation
- Use Python 3.12 or lower



### Coding

#### Setup venv
> Note: some requirements are not in conda, it is better to use a Python venv and to install requirements with pip

Create virtual environment in the project root folder
```
python -m venv venv
```

Activate the venv

Linux:
```
source /home/BENUTZER/venv-test/bin/activate
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

#### Packaging
With activated venv:
```
pip install PyInstaller
```

In case of any problems, try:
```
pip3 install --upgrade PyInstaller pyinstaller-hooks-contrib
```

#### Translation
Update translations with:
```
pyside6-lupdate bimsemantic/ui/*.py -ts ../bimsemantic/i18n/bimsemantic_de.ts
```

Edit the translations in QtLinguist and then release translation with:
```
pyside6-lrelease bimsemantic/i18n/bimsemantic_de.ts
```