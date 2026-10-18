![DxMediaCenter](https://i.ibb.co/5gTSN7tk/Dx.png)

# DxMediaCenter

DxMediaCenter ist ein eleganter, ressourcenschonender und lokaler Medien-Hub im modernen **Premium Dark Style**. Die Anwendung scannt Verzeichnisse vollautomatisch nach Filmen sowie Serienfolgen, strukturiert diese übersichtlich in Sektionen und bietet einen integrierten, voll funktionsfähigen Mediaplayer auf VLC-Basis. 

---

## ✨ Features

- **Automatisches Parsen & Gruppieren:** Intelligente Erkennung von Serienstrukturen (z. B. `S01E02`, `1x04`, `Episode X`) mit automatischer Sortierung nach Staffeln und Episoden. Einzelne Filme werden sauber separiert gelistet.
- **Integrierter High-Performance Player:** Nahtlose Wiedergabe aller gängigen Videoformate (`.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv` etc.) durch die native Einbindung des VLC-Kerns via `python-vlc`.
- **Intelligente Fortschrittsspeicherung:** Das Programm merkt sich die exakte Wiedergabeposition sekundengenau. Videos können im Tab "Aktive Filme" oder direkt in der Serienübersicht mit einem Klick fortgesetzt werden.
- **Fortlaufende Wiedergabe (Autoplay):** Nach dem Ende einer Serienepisode startet der Player auf Wunsch automatisch die nachfolgende Episode.
- **Integrierte Lautstärkeregelung:** Direkte Anpassung der Audiolautstärke im Player-Panel. Die bevorzugte Lautstärke wird sitzungsübergreifend gespeichert.
- **Premium UI/UX:** Entwickelt mit `CustomTkinter` für eine flüssige, hardwarebeschleunigte Benutzeroberfläche im modernen Dark-Design inklusive Windows 11 Snap-Layouts und abgerundeten Ecken.
- **Smarte Steuerung:** Automatisches Ausblenden der Player-Kontrollen bei Inaktivität der Maus sowie komfortable Hotkeys (z. B. `Leertaste` für Pause, `Esc` zum Schließen).
- **Vollständige Datensouveränität:** Alle Daten, Pfade und Verläufe werden ausschließlich lokal in einer `state.json` innerhalb des Benutzer-Anwendungsordners (`AppData`) gesichert. Keine Cloud-Anbindung, kein Tracking.

---
WICHTIG, der Offizielle VLC Mediaplayer muss auf dem Pc Installiert sein.

## 🛠️ Tech-Stack

- **Sprache:** Python 3.12+
- **GUI-Framework:** CustomTkinter (Tkinter-Erweiterung für modernes App-Design)
- **Medien-Engine:** python-vlc (VLC Media Player Bindings)
- **Datenstruktur:** JSON (Lokale Persistenz)


## 📝 Lizenz & Autor

- **Entwickler:** Lets Chico / Christopher K.

