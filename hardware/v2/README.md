# Hardware v2 – Steuerplatine

| Datei | Inhalt |
|---|---|
| `gen_schematic.py` | Erzeugt den Schaltplan (die Schaltung ist in `build()` definiert) |
| `kicad/balcon_irrigation_v2.kicad_sch` | Generierter KiCad-9-Schaltplan (A3, 1 Blatt) |
| `kicad/balcon_irrigation_v2.kicad_pro` | KiCad-Projekt |
| `kicad/balcon_irrigation_v2.pdf` | Schaltplan als PDF |
| `gen_layout.py` | Erzeugt und routet die Platine (Platzierung in `placement()`) |
| `kicad/balcon_irrigation_v2.kicad_pcb` | Platine, 100 × 100 mm, 2 Lagen |
| `kicad/balcon_irrigation_v2_top.pdf` / `_bottom.pdf` | Ober- und Unterseite als PDF |

Der Schaltplan wird **nicht von Hand editiert**, sondern neu generiert:

```sh
python3 gen_schematic.py kicad                                    # braucht KiCad-9-Symbolbibliotheken
kicad-cli sch erc --severity-all kicad/balcon_irrigation_v2.kicad_sch
kicad-cli sch export pdf kicad/balcon_irrigation_v2.kicad_sch
```

Die Bibliotheken liegen standardmäßig unter `/usr/share/kicad`, ein anderer Ort geht über `KICAD_SHARE=...`.
Die UUIDs sind deterministisch, deshalb erzeugt derselbe Code mit denselben Bibliotheken (9.0.2) eine byte-identische Datei.
Die Verbindungen laufen über Netz-Labels und Power-Symbole an jedem Pin, nicht über gezeichnete Leitungen.

## Layout

```sh
python3 gen_layout.py kicad/balcon_irrigation_v2.kicad_sch     # ~2 min, braucht pcbnew + Freerouting
kicad-cli pcb drc --schematic-parity kicad/balcon_irrigation_v2.kicad_pcb
```

Ablauf des Skripts:
1. Netzliste aus dem Schaltplan exportieren.
2. Footprints platzieren.
3. Umriss, Bestückungsdruck und Sperrfläche unter der Antenne anlegen.
4. Leiterbahnen mit Freerouting verlegen.
5. Erst danach die GND-Flächen auf beiden Lagen gießen.

Netzklassen: `Power` (+5V, VIN, PUMPx_N) 0,8 mm, `Ground` 0,5 mm, sonst 0,25 mm.
Freerouting liefert bei jedem Lauf ein etwas anderes Ergebnis.
Das eingecheckte `.kicad_pcb` ist der geprüfte Stand.

Platzierung:
- **Links:** Versorgung (Hohlbuchse, Schraubklemme, Sicherung, Verpolschutz, Elko)
- **Oben:** Sensor-, Tank- und I²C-Buchsen
- **Mitte:** DevKit, Antenne rechts über dem Platinenrand, USB links
- **Unten:** 5 Pumpenklemmen mit Treibern
- **Rechts:** Erweiterungsleiste
- **Ecken:** 4 × M3-Bohrungen

## Schaltung

**Versorgung:** 5 V über Hohlbuchse oder Schraubklemme, dann PTC-Sicherung (2 A),
dann Verpolschutz (AO3401A, P-MOSFET high-side), dann `+5V`.
Dazu ein Pufferelko 1000 µF und 100 nF.
`+5V` speist die Pumpen und den 5V-Pin des DevKits. `+3V3` kommt vom Regler des DevKits.

**ESP32-DevKitC V4:** steckt auf 2× Buchsenleiste 1×19 mit 25,4 mm Reihenabstand.
Die Pinbelegung steht in [`docs/v2-hardware.md`](../../docs/v2-hardware.md).

**Pumpenkanal (5×):**
- GPIO → 100 Ω → Gate AO3400A, mit 10k-Pulldown am Gate
- Low-side-Schaltung
- Schottky SS14 als Freilaufdiode zu `+5V`
- Anschluss über Schraubklemme (`+5V` / `PUMPx_N`)

**Sensorkanal (5×):**
- JST-XH 3-polig (GND / 3V3 / AOUT)
- RC-Tiefpass 1 kΩ + 100 nF vor dem ADC1-Pin

**Peripherie:**
- Tank-Schwimmer (JST-XH 2-polig, 10k-Pull-up, RC-Entprellung) an GPIO39
- I²C (JST-XH 4-polig, GND/3V3/SCL/SDA, 4,7k Pull-ups)
- Status-LED an GPIO27
- Erweiterungsleiste mit GPIO 4/13/16/17
- 4× Montageloch M3

LCSC-Nummern (JLC Basic Parts) sind als Feld `LCSC` hinterlegt.
Für Elko, PTC und Steckverbinder fehlen sie noch.

## Vor dem Layout prüfen

- [ ] **DevKit-Variante:** Reihenabstand und Pinfolge am eigenen Board nachmessen.
  Es gibt viele Klone mit 30 Pins oder anderer Breite.
- [ ] **USB + externe 5 V gleichzeitig:** Prüfen, ob das DevKit eine Diode zwischen USB-5V und dem 5V-Pin hat.
  Sonst beim Flashen über USB das Netzteil abziehen.
- [ ] **Pumpenstrom messen:** Anlauf- und Dauerstrom bestimmen. Davon hängen PTC, Leiterbahnbreite und Netzteil ab.
- [ ] **LCSC-Nummern** und Lagerbestand bei JLCPCB prüfen. Fehlende Teile ergänzen: PTC 1812, Elko, XH-Buchsen, Schraubklemmen.
- [ ] **Sensor-Stecker:** Der DFRobot-Sensor hat am Modul einen PH2.0-Stecker.
  Kabel auf JST-XH umcrimpen oder auf der Platine PH2.0 verwenden.
