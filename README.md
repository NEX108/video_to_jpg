
# Video to JPG Frame Extractor (Tkinter + OpenCV)

Dieses Projekt stellt ein **lokales Python-Tool mit grafischer Benutzeroberfläche (Tkinter)** bereit, um aus Videodateien **Einzelbilder (JPG)** mit frei einstellbarer Bildrate (FPS) zu extrahieren.

Das Tool richtet sich insbesondere an technische und wissenschaftliche Anwendungsfälle (z. B. Datensatzerstellung, Computer Vision, Machine Learning), bei denen reproduzierbare und zeitbasierte Frame-Extraktion erforderlich ist.

---

## Features

- Grafische Benutzeroberfläche (Tkinter)
- Auswahl beliebiger Videoformate, die von **OpenCV** unterstützt werden (z. B. mp4, avi, mkv)
- Zeitbasierte Frame-Extraktion (nicht nur jedes n-te Frame)
- Frei einstellbare FPS (z. B. 5–120 FPS)
  - Automatische Begrenzung auf die **native FPS** des Videos
- Automatische Nummerierung der Bilder:
  - `Name_1.jpg`, `Name_2.jpg`, ...
- Standardmäßig:
  - Bildname = Videoname
  - Speicherort = Ordner des Videos
- Ausgabe der Bilder in einem **eigenen Unterordner**
- Fortschrittsanzeige: `x von y Frames`
- Abbrechen-Funktion während der Verarbeitung
- Optionales Schreiben von **EXIF-Metadaten**
  - Frame-Index
  - Zeitstempel
  - Native FPS / Ziel-FPS
  - Quelle (Videodatei)
  - **Nicht sichtbar im Bild**, nur Metadaten

---

## Voraussetzungen

- Linux (getestet unter Ubuntu 24)
- Python ≥ 3.10
- System mit GUI-Unterstützung (Tkinter)

---

## Installation

### 1. Virtuelle Umgebung erstellen

```bash
python3 -m venv cam
source cam/bin/activate
python -m pip install --upgrade pip
```

### 2. Abhängigkeiten installieren

```bash
pip install opencv-python pillow piexif
```

---

## Starten des Programms

```bash
python video_to_jpg_ui.py
```

Nach dem Start öffnet sich die grafische Oberfläche.

---

## Bedienung

1. **Video auswählen**
   - Beliebige Videodatei (alle von OpenCV unterstützten Formate)

2. **FPS festlegen**
   - Ziel-FPS für die Extraktion
   - Wird automatisch auf die native FPS des Videos begrenzt

3. **Bild-Basisname**
   - Standard: Name der Videodatei
   - Bilder werden automatisch durchnummeriert

4. **Speicherort**
   - Standard: Ordner der Videodatei
   - Es wird automatisch ein Unterordner mit dem Bildnamen erstellt

5. **EXIF-Metadaten (optional)**
   - Aktivierbar per Checkbox
   - Keine sichtbaren Overlays im Bild

6. **Start**
   - Fortschritt wird live angezeigt
   - Vorgang kann jederzeit abgebrochen werden

---

## Technische Details

- Frame-Auswahl erfolgt **zeitbasiert**
- Berechnung über native FPS des Videos
- Keine Frame-Duplikation bei zu hoher Ziel-FPS
- Threading für UI-Reaktionsfähigkeit
- Robuste Fehlerbehandlung bei ungültigen Videos oder Abbruch

---

## Typische Anwendungsfälle

- Datensatz-Erstellung für Computer Vision
- Small Object Detection / Object Detection
- Frame-Sampling für Machine Learning
- Videoanalyse und Debugging
- Embedded- & Edge-Vision-Workflows

---

## Einschränkungen

- Die Genauigkeit von `Total Frames` hängt von den Video-Metadaten ab
- Manche exotische Codecs liefern über OpenCV keine exakten Frame-Zahlen
- Sehr hohe FPS-Werte sind durch die native Video-FPS limitiert

---

## Lizenz

MIT License

---

## Hinweis

Dieses Tool verarbeitet Videos **lokal**. Es findet keine Netzwerkkommunikation und keine Datenübertragung statt.
