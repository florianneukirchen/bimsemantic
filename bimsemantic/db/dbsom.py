import csv
import os
import sys
import json
import argparse


def name_and_level(row):
    """Extrahiere Name und Level aus einer Zeile des SOM-CSVs.
    
    Die ersten Spalten des CSVs enthalten den Namen des Objekts,
    wobei die Einrückung die Hierarchie repräsentiert
    (die anderen Spalten sind leer). Wie viele Spalten für den Namen 
    stehen ist nicht festgelegt, die Gliederung in Gruppen und 
    Teilgruppen ist in den verschiedenen Fachmodellen unterschiedlich.

    Die Funktion gibt level 0 zurück, wenn der Name in der ersten
    Spalte steht, level 1, wenn der Name in der zweiten Spalte steht, usw.

    :param row: Eine Zeile des SOM-CSVs
    :type row: list
    :return: Tuple mit Name und Level

    - name (str): Der Name des Objekts
    - level (int): Die Hierarchieebene des Objekts
    """
    for i, s in enumerate(row):
        if s:
            return s, i
        

def row_to_dict(row, columns):
    """Konvertiere eine Zeile des SOM-CSVs in ein Dictionary.
    
    Die Funktion nimmt eine Zeile des SOM-CSVs und die Spaltennamen
    und gibt ein Dictionary zurück, das die Werte der Spalten enthält.
    Die Spalte "Werteliste" wird als Liste von Strings zurückgegeben.
    
    :param row: Eine Zeile des SOM-CSVs
    :type row: list
    :param columns: Die Spaltennamen des CSVs
    :type columns: list
    """
    namecolumns = columns.index("Name")
    name, level = name_and_level(row)

    d = {}
    d['Name'] = name

    # Namen-Spalten entfernen
    columns = columns[namecolumns+1:]
    row = row[namecolumns+1:]

    # Durch restliche Spalten iterieren
    
    # Die Spalten mit den Leistungsphasen/ Andendungsfällen
    # haben Spaltentitel wie "Lph-1-2D" (wobei 2D Abk. für
    # Anwendungsfall "Erstellung von Plänen" ist) und in der
    # Zelle steht dann '-' für nein, '*' für ja, geerbt, oder
    # Häckchen (bzw. im exportierten CSV '?') für ja.
    # Relevant ist dies nur bei Attributen (bei Gruppen, Elementen etc.
    # steht auch irgendwas, aber das ergibt sich indirekt aus den Attributen)

    # Wenn immer eine Lph-Spalte nicht '-' ist, bedeutet das ja
    # Wir machen aber eine Liste mit Leistungsfällen und eine andere mit Anwendungsfällen
    # d.h. es interessiert nur der Name der Spalte
    
    leistungsphasen = set()
    anwendungsfaelle = set()
    
    for i, col in enumerate(columns):
        if row[i]:
            # If Leistungsphasen-Spalte
            if col.startswith("Lph"):
                if not d["Typ"] == "Eigenschaft":
                    continue
                if row[i] == '-':
                    # Diese Lph/Anw ist nein
                    continue
                _, lph, anw = col.split("-")
                leistungsphasen.add(int(lph))
                anwendungsfaelle.add(anw)
            else:
                # Alle anderen Spalten
                d[col] = row[i]

    leistungsphasen = list(leistungsphasen)
    anwendungsfaelle = list(anwendungsfaelle)

    if len(leistungsphasen) > 0:
        d["Lph"] = leistungsphasen
        d["Anw"] = anwendungsfaelle
    
    # In der SOM-Liste (vers. 2.1) sind die meisten Fachmodelle in
    # "Gruppe", "Teilgruppe" (nur manchmal) gegliedert, dann
    # Elemente mit Property Sets und Attributen.

    # In der Originaltabelle (die wir hier verwenden) sind die Begriffe 
    # anders: hier haben wir statt Gruppe, Teilgruppe und Property Set 
    # immer "Typ" == "Gruppe" und "Eigenschaft" statt "Attribut" 

    # Dies ersetzen wir im folgenden mit dem korrekten Begriff.
    # "Element" kann in der Tabelle level 0 (Fachmodell Umwelt),
    # level 1 oder 2 haben.
    
    if d["Typ"] == "Gruppe":
        if level == 0:
            pass
        elif namecolumns > 3 and level == 1:
            # D.h. bei allen außer Umwelt mit Gruppe in level 1
            d["Typ"] = "Teilgruppe"
        else:
            d["Typ"] = "Property Set"

    elif d["Typ"] == "Eigenschaft":
        d["Typ"] = "Attribut"
    
    # Werteliste splitten
    try:
        d["Werteliste"] = d["Werteliste"].split(",") 
        d["Werteliste"] = [s.strip() for s in d["Werteliste"]]       
    except KeyError:
        pass
    return d

def som_csv_to_tree(filename, encoding='iso-8859-1', delimiter=";"):
    """SOM-Liste CSV-Datei zu name und dict
    
    Öffnet ein CSV mit einem Fachmodell des 
    semantischen Objektmodells (SOM) der Deutschen Bahn
    und gibt den Namen des Fachmodells und das SOM als
    ein baumartiges verschachteltes Dictionary zurück.

    Die jeweiligen Kindselemente sind über den Schlüssel
    'childs' erreichbar.

    :param filename: Dateiname bzw. Pfad zur CSV-Datei
    :type filename: str
    :param encoding: Encoding der Datei, default 'iso-8859-1' (Standard bei Export aus Excel ist 'iso-8859-1')
    :type encoding: str
    :param delimiter: Trennzeichen in der CSV-Datei
    :type delimiter: str
    :returns:
        tuple: (fachmodell, modeltree)

        - fachmodell (str): Name des Fachmodells
        - modeltree (dict): Das SOM als baumartiges verschachteltes Dictionary.
    """
    with open(filename, encoding=encoding) as file:
        reader = csv.reader(file, delimiter=delimiter)
        row = next(reader)
        fachmodell = row[0]  # Erste Zeile: Titel des Fachmodells

        if not fachmodell:
            raise ValueError("Fachmodellname ist leer")

        modeltree = {} 
        # Keys in modeltree sind die levels in der Hierarchie
        # Am Ende enthält modeltree[0] den gesamten Baum 
        modeltree[0] = {}
        modeltree[0]["Name"] = fachmodell
        modeltree[0]["Typ"] = "Fachmodell"
        modeltree[0]["childs"] = {}

        columns = next(reader) # Zweite Zeile enthält Columnheaders

        for row in reader:
            name, level = name_and_level(row)
            type = row[columns.index("Typ")]
            node = row_to_dict(row, columns)

            modeltree[level]["childs"][name] = node

            if type in ["Gruppe", "Teilgruppe", "Element", "Property Set"]:
                node["childs"] = {}
                modeltree[level+1] = node
                
    return fachmodell, modeltree[0] # Level 0 contains all children of the other levels


def csv_filepaths_in_folder(path=None):
    """Return a list of all CSV files in a folder, excluding Vorblatt CSVs.
    
    :param path: The path to the folder
    :type path: str
    :return: List of filepaths
    :rtype: list
    """
    if path is None:
        path = os.getcwd()
    files = os.listdir(path=path)
    files = [os.path.join(path, f) for f in files if f.lower().endswith(".csv")]
    return files


def folder_csv_files_to_som_dict(path=None, encoding='iso-8859-1', delimiter=";"):
    """Convert all CSV files in a folder to a SOM dictionary.
    
    :param path: The path to the folder
    :type path: str
    :param encoding: Encoding of the CSV files
    :type encoding: str
    :return: Dictionary with SOMs
    :rtype: dict
    """
    files = csv_filepaths_in_folder(path)
    som = {}
    for file in files:
        try:
            name, d = som_csv_to_tree(file, encoding=encoding, delimiter=delimiter)
            som[name] = d
        except Exception as e:
            print(f"Ignoriere Datei mit Parsing-Fehler:\n{file}\n{e}")
    return som


if __name__ == "__main__":
    package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, package_root)
    from bimsemantic import __version__

    description = """CSVs der DB-SOM-Fachmodelle in JSON umwandeln.
        Extrahiert die Daten aus der SOM-Liste der Deutschen Bahn
        (Version 2.1), bereitet sie auf und speichert sie als JSON.
        Für jedes Fachmodell muss in Excel jeweils die "Originaltabelle" 
        in eine CSV-Datei exportiert werden. Dateien, die nicht erfolgreich
        geparst werden können, werden ignoriert.
        """

    parser = argparse.ArgumentParser(prog="dbsom", description=description)
    parser.add_argument('--version', action='version', version="{prog}s {version}".format(prog="%(prog)", version=__version__))
    parser.add_argument("-p", "--path", help="Pfad zum Ordner mit CSV-Dateien (default: aktuelles Arbeitsverzeichnis)", default=None)
    parser.add_argument("-o", "--output", help="Dateiname für die JSON-Datei (default: som.json)", default="db_som.json")
    parser.add_argument("-e", "--encoding", help="Encoding der CSV-Dateien (default: iso-8859-1)", default="iso-8859-1")
    parser.add_argument("-d", "--delimiter", help="Trennzeichen in der CSV-Datei (default: ;)", default=";")

    args = parser.parse_args()

    som = folder_csv_files_to_som_dict(path=args.path, encoding=args.encoding, delimiter=args.delimiter)

    with open(args.output, 'w') as file:
        json.dump(som, file)