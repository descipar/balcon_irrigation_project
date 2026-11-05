# Version 2 – Platine (PCB)

## Ziel

2-lagige Trägerplatine, gefertigt **und bestückt bei JLCPCB**.

### Inhalt
- Sockel (Buchsenleisten) für ein **ESP32 DevKit** – tauschbar
- **5 Pumpenkanäle**: Logic-Level-MOSFET, Gate-Widerstand, Pulldown, Schottky-Diode, Schraubklemme
- **5 Sensorbuchsen** JST-XH 3-polig (3,3 V / GND / Signal → ADC1)
- **5V-Eingang** (Hohlbuchse + Schraubklemme), Sicherung, Pufferelko
- Eingang für **Schwimmerschalter** (Tank leer)
- **I²C-Stiftleiste** (Display, Temp./Feuchtesensor)
- Status-LED
- Breite Leiterbahnen für Pumpenströme, Montagelöcher

### Bauteilauswahl
SMD-Bauteile bevorzugt aus der **JLC Basic Parts**-Bibliothek (keine Zusatzgebühr).
Steckverbinder/Schraubklemmen ggf. als Extended Parts oder Handbestückung.

## Toolchain

Design komplett skriptbasiert auf **`serviceplasma`** (Debian 13, arm64):

| Tool | Version | Zweck |
|---|---|---|
| KiCad (`kicad-cli`, Python `pcbnew`) | 9.0.2 | Schaltplan, Layout, DRC/ERC, Export |
| Freerouting | 2.5.0 (`~/tools/freerouting/`) | Autorouter |
| Java (openjdk-25-jre-headless) | 25 | für Freerouting (2.5.0 braucht Java ≥ 25) |

Installiert ohne 3D-Modelle (`kicad-packages3d`), da für die Fertigung nicht nötig.

### Ablauf
1. Schaltung/Netzliste per Python erzeugen
2. Platinenumriss, Footprints platzieren
3. Routing mit Freerouting (DSN-Export → Route → SES-Import)
4. DRC/ERC mit `kicad-cli`
5. Rendern (SVG/PNG) zur Sichtprüfung
6. Export: Gerber + Bohrdaten, BOM, CPL (Bestückungsdatei) im JLC-Format

**Vor der Bestellung:** Ergebnis in KiCad öffnen und manuell prüfen –
der Autorouter liefert funktionale, aber nicht unbedingt schöne Platinen.

## Status

- [x] Konzept & Bauteilauswahl (siehe `v2-hardware.md`)
- [x] Toolchain auf `serviceplasma` installiert
- [x] Schaltplan (`hardware/v2/`, ERC: 0 Fehler / 0 Warnungen) – Review durch Kai offen
- [x] Layout & Routing (`hardware/v2/gen_layout.py`, 100 × 100 mm, 2 Lagen, Freerouting)
- [x] DRC: 0 Fehler, 0 offene Verbindungen (nur Silkscreen-Überlappungen) – Review durch Kai offen
- [ ] Fertigungsdaten (Gerber, BOM, CPL)
- [ ] Bestellung (manuell durch Kai)
