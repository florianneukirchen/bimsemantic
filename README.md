# BIM Semantic Viewer

BIM Semantic Viewer
präsentiert die Elemente von IFC-Dateien und ihre Semantik in mehreren 
unterschiedlich aufgebauten Baumansichten. Neben den vorgegebenen Ansichten 
können auch benutzerdefinierte Baumansichten erstellt werden. Die Werte 
ausgewählter Attribute können in Tabellenspalten eingeblendet werden.
Ein Panel an der Seite zeigt alle Details des gewählten Elements an. 
Weitere Panels fassen alle Property Sets bzw. Quantity Sets und darin verwendete Werte zusammen.
Zudem ist eine Validierung der Daten anhand von in IDS-Dateien definierten Regeln 
möglich, wobei auch ein Editor für diese Regeln bereitgestellt wird.  
Das semantische Objektmodell (SOM) der Deutschen Bahn kann ebenfalls eingelesen
und angezeigt werden, wobei eine automatische Suche nach dem Wert einer 
bestimmten Property eingestellt werden kann, um zu einem gewählten Objekt 
des IFC-Modells den relevanten Eintrag in der SOM-Liste zu finden.
Das Programm ermöglicht es, die semantische Struktur von BIM-Modellen zu untersuchen
sowie schnell fehlende Attribute und Tippfehler zu erkennen. 



## Installation 

Mit PyInstaller erzeugte ausführbare Dateien können ohne weitere Installation 
mit einem Doppelklick gestartet werden. 

Die folgenden Angaben betreffen nur die Installation des Source Codes.
### Python

Python must be installed on the system.
The required package IfcOpenShell is compatible with Python 3.9 to 3.12.

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
### Translation
(Commands in the root directory of the project with venv enabled)

Update translations:
```
pyside6-lupdate bimsemantic/ui/*.py -ts bimsemantic/i18n/bimsemantic_de.ts
```

Edit the translations in QtLinguist 
```
pyside6-linguist bimsemantic/i18n/bimsemantic_de.ts
```

and then release translation with:
```
pyside6-lrelease bimsemantic/i18n/bimsemantic_de.ts
```

### Resources

Icons have to be added to resources.qrc. This file is compiled with:

```
pyside6-rcc resources.qrc -o resources.py
```


### Packaging with PyInstaller
This section explains how to create a package with PyInstaller.

With activated venv:
```
pip install PyInstaller
```

PyInstaller uses a spec file for configuration.
To create a spec file for a project, run with activated venv:
```
cd bimsemanticviewer
pyinstaller app.py
```

The spec file has to be edited: Hidden imports and required files such as the
IFC rules and ids.xsd have to be packaged as well. The source code contains the edited 
files for windows (`app.spec.windows`) and Linux (`app.spec.linux`).

Now run
```
pyinstaller app.spec
```
And the exe will be in the `dist` folder

In case of any problems, try:
```
pip3 install --upgrade PyInstaller pyinstaller-hooks-contrib
```

Note to self: git pull with github cli: gh repo sync

