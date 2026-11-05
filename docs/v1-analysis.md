# Analyse Version 1 (Arduino Uno)

Bezieht sich auf `vscode_workspace/BalconIrrigation/src/main.cpp` und die Fritzing-Schaltung.

## Ablauf

```
loop:
  delay(30 s)
  A0, A1 lesen
  für jeden Topf: Wert > 350 → Pumpe 3 s an
```

## Bugs & Schwachstellen

### 1. Falsche Messwerte bei kurzer Wartezeit
Die Git-Historie zeigt, dass `waitingTime` von 1 s auf 30 s erhöht wurde, weil die Sensoren
sonst "falsche Werte" lieferten. Kapazitive Sensoren brauchen aber keine 30 s zum Einschwingen.
Wahrscheinlichere Ursachen:

- **Pumpen ziehen die 5V-Versorgung runter** (Uno-5V bzw. USB). Der Sensorausgang (555-basiert)
  und die ADC-Referenz verschieben sich, dazu kommen Motorstörungen. → *Hauptverdacht, Hardware.*
- **ADC-Multiplexer**: `analogRead(A0)` direkt gefolgt von `analogRead(A1)` – der erste Wert
  nach einem Kanalwechsel ist oft ungenau. Dummy-Read + Mittelwert hilft.
- **Keine Glättung**: Einzelmessung statt Mittelwert/Median.

### 2. `int`-Überlauf bei Zeiten
Auf dem Uno ist `int` 16 Bit (max. 32767). `waitingTime = 30000` passt gerade noch –
bei z. B. 60000 wird der Wert negativ und `delay()` wartet ~49 Tage.
→ Zeiten als `unsigned long`.

### 3. Überwässerung
3 s pumpen, 30 s später erneut messen – das Wasser ist oft noch nicht am Sensor,
also wird erneut gepumpt. Es fehlen:
- **Einsickerzeit** nach dem Gießen (10–30 min)
- **Hysterese** (z. B. gießen ab 400, "ok" erst unter 300)
- **Tageslimit** pro Topf

### 4. Keine Fehlererkennung
- Abgesteckter/defekter Sensor → hoher/zufälliger Wert → Pumpe läuft dauernd
- Leerer Tank → Pumpe läuft trocken (erkennbar: Wert sinkt trotz Pumpen nicht)

### 5. Keine Kalibrierung
Fester Schwellwert 350 für alle Töpfe, obwohl Sensoren stark streuen.
Besser: pro Sensor Trocken-/Nasswert (Luft/Wasser) einmessen → 0–100 %.

### 6. Code-Qualität
- Copy-Paste pro Pflanze statt Array/Struct + Schleife
- `currentPlant0 = 0;` direkt vor `analogRead` ist wirkungslos
- Unübersichtliche Serial-Ausgabe, gemischte Deutsch/Englisch-Namen
- Die `.ino`-Version liest zwei Sensoren, gießt aber nur Topf 1

## Hardware (Fritzing)

Uno, 5× DFRobot Capacitive Soil Moisture Sensor, 5× DC-Pumpe, je über
**BC337** (mit Basiswiderstand) low-side geschaltet, **1N4148** als Freilaufdiode.

- 1N4148 ist als Freilaufdiode für Motoren knapp → 1N5819 (Schottky) o. ä.
- Pumpen sollten eine eigene Versorgung bzw. großen Pufferelko bekommen
