# Theaterplanung

Desktop-Tool (Python/Tkinter) zur Planung von Theaterproben: Schauspieler, Rollen, Szenen,
Abwesenheiten und Proben verwalten, Terminkonflikte erkennen und alles exportieren.

## Funktionen

| Tab | Inhalt |
| --- | --- |
| **Schauspieler** | Schauspieler anlegen, umbenennen, löschen |
| **Rollen** | Rollen mit Schauspieler und Wichtigkeit (1–5); Übersicht der Szenen, Proben und Abwesenheiten je Rolle; Spaltenfilter |
| **Szenen** | Szenen mit Rollen und optional geplanter Probenzahl; zeigt Proben, Fortschritt („Geprobt“) und Abwesenheiten |
| **Abwesenheiten** | Zeiträume je Schauspieler; zeigt verpasste Proben; Filter nach Schauspieler und Datum |
| **Proben** | Allgemeine Proben oder Proben mit mehreren Szenen, einmalig/wöchentlich/monatlich; Vorschlag der am besten besetzbaren Szenen; „Durchgeführt“ per Klick |
| **Kalender** | Monatsansicht der Proben; Verfügbarkeitsprüfung: markiert Tage, an denen alle gewählten Rollen anwesend sind |

**Speichern/Laden:** Menü *Datei → Speichern… / Laden…* (JSON). Es gibt **kein automatisches
Speichern**, bitte vor dem Beenden speichern. Eine Beispieldatei liegt unter
[`examples/beispiel.json`](examples/beispiel.json).

**Export:** Menü *Datei → Exportieren…* als CSV, TXT (je Bereich eine Datei) oder PDF
(eine Datei, optional mit Monatskalendern).

## Installation und Start

Voraussetzung: Python 3.9+ (Tkinter ist bei der Windows-Installation von Python enthalten).

```
pip install -r requirements.txt
python main.py
```

## EXE bauen (ohne Konsolenfenster)

```
.\build.ps1
```

Ergebnis: `dist\Theaterplanung.exe`

> **Hinweis:** In `build.ps1` wird standardmäßig `python` aus dem PATH verwendet. Ist Python nicht im
> PATH, kann ein eigener Pfad übergeben werden, z. B. `.\build.ps1 -Python "C:\Path\To\Python\python.exe"`.
> Der Pfad ist nur ein **Platzhalter** und muss durch den eigenen ersetzt werden.

## Projektstruktur

```
main.py              Hauptfenster, Menü, Speichern/Laden, Export-Dialog
data.py              Datenmodell und Logik (Abwesenheiten, Szenenvorschläge, Umbenennen/Löschen)
exporter.py          CSV-, TXT- und PDF-Export
ui/                  Ein Modul je Tab, gemeinsame Hilfen in common.py
examples/            Beispieldaten
build.ps1            EXE-Build mit PyInstaller
```
