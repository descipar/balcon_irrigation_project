# Balcony Irrigation Project

Automatische Balkonbewässerung: kapazitive Bodenfeuchtesensoren messen die Erde,
kleine 5V-Pumpen gießen bei Bedarf nach.

> **Status:** Version 1 (Arduino Uno, Breadboard) hat funktioniert, hatte aber Bugs
> und war wenig "intelligent". Version 2 (ESP32 + eigene Platine + ESPHome/Home Assistant)
> ist in Planung – siehe [`docs/`](docs/).

## Repository-Struktur

| Pfad | Inhalt |
|---|---|
| `vscode_workspace/BalconIrrigation/` | **Firmware v1** (PlatformIO, Arduino Uno) – letzte lauffähige Version |
| `arduino_workspace/balcon_irrigation/` | Ältere Arduino-IDE-Version (veraltet, gießt nur Topf 1) |
| `arduino_workspace/GraphicsTestExample/` | u8g2-Beispiel aus einem verworfenen Display-Versuch |
| `fritzing_workspace/` | Schaltung v1 (Fritzing): Uno, 5× Sensor, 5× Pumpe über BC337 + 1N4148 |
| `stl/` | 3D-Druckteile: Filmdosen-Behälter (12/20/47 mm), Deckel, Wasserverteiler |
| `docs/` | Analyse von v1, Hardware-Konzept und PCB-Plan für v2 |

## Version 1 (Arduino Uno)

- 2 von 5 Kanälen aktiv: Sensoren an `A0`/`A1`, Pumpen an Pin `10`/`11`
- Alle 30 s messen; Wert > 350 (= trocken) → Pumpe 3 s an
- Bauen/Flashen mit PlatformIO:
  ```sh
  cd vscode_workspace/BalconIrrigation
  pio run -t upload && pio device monitor
  ```

Bekannte Probleme (Details in [`docs/v1-analysis.md`](docs/v1-analysis.md)):
Überwässerungsgefahr ohne Einsickerzeit, keine Hysterese, keine Erkennung
von Sensorfehlern oder leerem Tank, Messwerte gestört durch Pumpen an der gleichen 5V-Versorgung,
`int`-Überlauf bei Wartezeiten > 32767 ms.

## Version 2 (geplant)

- **ESP32** statt Uno – WLAN, NTP-Zeit, OTA-Updates
- **Eigene Platine**, gefertigt und bestückt bei JLCPCB (KiCad)
- 5 Kanäle, Logic-Level-MOSFETs für 5V-Pumpen, separate Pumpenversorgung
- **ESPHome + Home Assistant** für Logik, Verlauf und Benachrichtigungen

Siehe:
- [`docs/v1-analysis.md`](docs/v1-analysis.md) – Bugs & Schwachstellen von v1
- [`docs/v2-hardware.md`](docs/v2-hardware.md) – ESP32-Konzept, Pumpenansteuerung, Pinbelegung
- [`docs/v2-pcb.md`](docs/v2-pcb.md) – PCB-Plan und Toolchain (KiCad auf `serviceplasma`)
