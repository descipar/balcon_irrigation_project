# Version 2 – Hardware-Konzept (ESP32)

## Warum ESP32 statt Uno

| | Uno | ESP32 |
|---|---|---|
| WLAN (Home Assistant, Logging, Push bei leerem Tank) | – | ✓ |
| Uhrzeit per NTP (morgens/abends gießen) | – | ✓ |
| OTA-Updates | – | ✓ |
| Analogeingänge | 6 × 10 Bit | 6 × 12 Bit nutzbar (ADC1, auch mit WLAN) |
| Logikpegel | 5 V | **3,3 V** |

## Entscheidungen

- **5 Kanäle**, **5V-Pumpen**
- Platine wird von **JLCPCB bestückt** (SMD-Teile aus der JLC-Bibliothek)
- Software: **ESPHome + Home Assistant**

## Pumpenansteuerung

Der BC337 aus v1 ist an 3,3 V ungeeignet: Für 200–400 mA Pumpenstrom bräuchte er
15–30 mA Basisstrom – mehr als ein ESP32-Pin liefern sollte.

**Lösung: Logic-Level-N-MOSFET pro Kanal, low-side**

```
  +5V Pumpe ───────┬──────────┐
                   │          │
                 Pumpe     Schottky (Kathode an +5V)
                   │          │
                   ├──────────┘
                 Drain
  GPIO ──[100Ω]── Gate     N-MOSFET, voll leitend bei Vgs ≤ 2,5 V (z. B. AO3400)
           │      Source
         [10k]      │
           │        │
  GND ─────┴────────┴──── GND (gemeinsam mit ESP32)
```

- **MOSFET** muss bei 2,5–3,3 V Gate-Spannung spezifiziert sein (AO3400, IRLML2502, …).
  IRLZ44N ist erst ab 4–5 V spezifiziert → ungeeignet.
- **10k Pulldown** am Gate: ESP32-Pins floaten beim Booten, sonst laufen Pumpen kurz an.
- **Schottky-Freilaufdiode** (z. B. SS14 / 1N5819) statt 1N4148.
- Optional PWM-Softstart (LEDC) gegen Einschaltstromspitzen.

## Stromversorgung

- **5V-Netzteil ≥ 2 A** speist Pumpen direkt und ESP32 über 5V/VIN
- **470–1000 µF Elko** an der Pumpenversorgung, Sicherung im Eingang
- Sensoren werden mit **3,3 V** versorgt → Ausgang bleibt sicher im ADC-Bereich

## Pinbelegung (ESP32 DevKit)

Festgelegt im Schaltplan (`hardware/v2/`), Board: **ESP32-DevKitC V4 (38 Pins, WROOM-32)**.

| Funktion | GPIO | Hinweis |
|---|---|---|
| Sensor 1–5 | 32, 33, 34, 35, 36 (VP) | nur **ADC1** – ADC2 geht nicht mit WLAN |
| Pumpe 1–5 | 18, 19, 23, 25, 26 | keine Strapping-Pins, bleiben beim Boot ruhig |
| I²C (SDA/SCL) | 21 / 22 | Display, Temp./Feuchte; 4,7k Pull-ups auf der Platine |
| Tank leer (Schwimmer) | 39 (VN) | Eingang, 10k Pull-up auf 3,3 V, Schalter gegen GND |
| Status-LED | 27 | |
| Erweiterung (frei) | 4, 13, 16, 17 | auf Stiftleiste herausgeführt |

**Meiden** für Ausgänge: GPIO 0, 2, 5, 12, 14, 15 (Strapping/Boot-Signale), 6–11 (Flash).
GPIO 16/17 sind bei WROVER-Modulen durch PSRAM belegt – daher nicht für Pumpen verwendet.

## Logik (ESPHome / Home Assistant)

Pro Topf ein Zustandsautomat: **MESSEN → GIESSEN → EINSICKERN → SPERRE**

- Kalibrierte Prozentwerte (Trocken-/Nasswert pro Sensor)
- Hysterese, Mittelwert über mehrere Messungen
- Einsickerzeit nach dem Gießen, Tageslimit pro Topf
- Sensorfehler-Erkennung (Wert außerhalb Kalibrierbereich)
- Tank-leer-Erkennung (Schwimmer und/oder: Feuchte steigt trotz Pumpen nicht)
- Gießen bevorzugt zu festen Uhrzeiten (morgens/abends)
