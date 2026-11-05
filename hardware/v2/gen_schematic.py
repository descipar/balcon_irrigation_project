#!/usr/bin/env python3
"""Generate the KiCad 9 schematic for the balcony irrigation controller v2.

Run on a machine with KiCad 9 libraries installed (default: /usr/share/kicad):

    python3 gen_schematic.py [out_dir]

Writes <out_dir>/balcon_irrigation_v2.kicad_sch (+ .kicad_pro). Connectivity is done
with net labels / power symbols on short wire stubs at every pin, so the
schematic is easy to generate and diff; the circuit is defined in build().
"""
import os
import sys
import uuid

KICAD = os.environ.get("KICAD_SHARE", "/usr/share/kicad")
SYMDIR = os.path.join(KICAD, "symbols")
FPDIR = os.path.join(KICAD, "footprints")
PROJECT = "balcon_irrigation_v2"
STUB = 2.54
POWER_NETS = {"+5V": "power:+5V", "+3V3": "power:+3V3", "GND": "power:GND"}


# --------------------------------------------------------------------------- s-expr
class Sym(str):
    """Unquoted atom."""


def parse(text):
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            tokens.append(c)
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while text[j] != '"':
                if text[j] == "\\":
                    j += 1
                buf.append(text[j])
                j += 1
            tokens.append(("STR", "".join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            tokens.append(Sym(text[i:j]))
            i = j
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        elif isinstance(t, tuple):
            stack[-1].append(t[1])
        else:
            stack[-1].append(t)
    return stack[0][0]


def dump(e, ind=0):
    pad = "\t" * ind
    if not isinstance(e, list):
        return fmt_atom(e)
    if all(not isinstance(x, list) for x in e):
        return pad + "(" + " ".join(fmt_atom(x) for x in e) + ")"
    out = pad + "(" + " ".join(fmt_atom(x) for x in e if not isinstance(x, list))
    for x in e:
        if isinstance(x, list):
            out += "\n" + dump(x, ind + 1)
    return out + "\n" + pad + ")"


def fmt_atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, bool):
        return "yes" if a else "no"
    if isinstance(a, (int, float)):
        v = round(float(a), 4)
        return str(int(v)) if v == int(v) else repr(v)
    return '"' + str(a).replace("\\", "\\\\").replace('"', '\\"') + '"'


def find(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]


def S(*a):
    return [Sym(a[0])] + list(a[1:])


_uid_counter = [0]


def uid():
    """Deterministic UUIDs so regenerating gives byte-identical output (clean diffs)."""
    _uid_counter[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{PROJECT}/{_uid_counter[0]}"))


# --------------------------------------------------------------------------- libs
_libcache = {}


def load_lib(lib):
    if lib not in _libcache:
        with open(os.path.join(SYMDIR, lib + ".kicad_sym"), encoding="utf-8") as f:
            root = parse(f.read())
        _libcache[lib] = {s[1]: s for s in find(root, "symbol")}
    return _libcache[lib]


def resolve_symbol(lib_id):
    """Return a flattened lib symbol named lib_id (handles 'extends')."""
    lib, name = lib_id.split(":")
    syms = load_lib(lib)
    sym = syms[name]
    ext = find(sym, "extends")
    if not ext:
        flat = [Sym("symbol"), lib_id] + [x for x in sym[2:]]
        return flat
    parent = resolve_symbol(lib + ":" + ext[0][1])
    pname = ext[0][1]
    child_props = {p[1]: p for p in find(sym, "property")}
    flat = [Sym("symbol"), lib_id]
    for x in parent[2:]:
        if isinstance(x, list) and x[0] == "property" and x[1] in child_props:
            flat.append(child_props.pop(x[1]))
        elif isinstance(x, list) and x[0] == "symbol":
            flat.append([Sym("symbol"), x[1].replace(pname, name, 1)] + x[2:])
        else:
            flat.append(x)
    # child-only properties go before the unit sub-symbols
    idx = next(i for i, x in enumerate(flat) if isinstance(x, list) and x[0] == "symbol")
    for p in child_props.values():
        flat.insert(idx, p)
        idx += 1
    return flat


def lib_pins(flat):
    pins = []

    def walk(e):
        for x in e:
            if isinstance(x, list):
                if x[0] == "pin":
                    at = find(x, "at")[0]
                    num = find(x, "number")[0][1]
                    name = find(x, "name")[0][1]
                    pins.append({"num": num, "name": name, "x": float(at[1]),
                                 "y": float(at[2]), "ang": float(at[3])})
                else:
                    walk(x)
    walk(flat)
    return pins


# --------------------------------------------------------------------------- schematic
class Schematic:
    def __init__(self):
        self.root_uuid = uid()
        self.lib_symbols = {}
        self.items = []
        self.refcount = {}
        self.pwrcount = 0
        self.footprints_missing = []

    def _lib(self, lib_id):
        if lib_id not in self.lib_symbols:
            self.lib_symbols[lib_id] = resolve_symbol(lib_id)
        return self.lib_symbols[lib_id]

    def _place(self, lib_id, x, y, ref, value, footprint="", rot=0, mirror=False,
               fields=None, hide_value=False):
        flat = self._lib(lib_id)
        x, y = round(x / 1.27) * 1.27, round(y / 1.27) * 1.27
        if footprint and os.path.isdir(FPDIR):
            lib, fp = footprint.split(":")
            if not os.path.exists(os.path.join(FPDIR, lib + ".pretty", fp + ".kicad_mod")):
                self.footprints_missing.append(footprint)
        props = {p[1]: p for p in find(flat, "property")}
        sym = S("symbol", S("lib_id", lib_id), S("at", x, y, rot))
        if mirror:
            sym.append(S("mirror", Sym("y")))
        sym += [S("unit", 1), S("exclude_from_sim", Sym("no")), S("in_bom", Sym("no") if ref.startswith("#") else Sym("yes")),
                S("on_board", Sym("no") if ref.startswith("#") else Sym("yes")), S("dnp", Sym("no")), S("uuid", uid())]
        values = {"Reference": ref, "Value": value, "Footprint": footprint,
                  "Datasheet": props.get("Datasheet", [0, 0, "~"])[2]}
        values.update(fields or {})
        for k, v in values.items():
            lp = props.get(k)
            if lp is not None:
                at = find(lp, "at")[0]
                px, py, pa = float(at[1]), float(at[2]), float(at[3])
                hidden = bool(find(find(lp, "effects")[0], "hide")) if find(lp, "effects") else False
            else:
                px, py, pa, hidden = 0, 0, 0, True
            if mirror:
                px = -px
            if rot:
                # move the field with the symbol but keep the text horizontal and readable
                c, s_ = {90: (0, 1), 180: (-1, 0), 270: (0, -1)}[rot]
                px, py, pa = px * c - py * s_, px * s_ + py * c, 0
            hide = hidden or k in ("Footprint", "Datasheet") or k not in ("Reference", "Value") \
                or (k == "Value" and hide_value)
            eff = S("effects", S("font", S("size", 1.27, 1.27)))
            if hide:
                eff.append(S("hide", Sym("yes")))
            sym.append(S("property", k, v, S("at", x + px, y - py, pa), eff))
        for p in lib_pins(flat):
            sym.append(S("pin", p["num"], S("uuid", uid())))
        sym.append(S("instances", S("project", PROJECT,
                                    S("path", "/" + self.root_uuid, S("reference", ref), S("unit", 1)))))
        self.items.append(sym)
        pins = {}
        for p in lib_pins(flat):
            px, py, ang = p["x"], p["y"], p["ang"]
            if mirror:
                px, ang = -px, (180 - ang) % 360
            # rotation (CCW, lib coordinates are Y-up)
            import math
            r = math.radians(rot)
            rx = px * math.cos(r) - py * math.sin(r)
            ry = px * math.sin(r) + py * math.cos(r)
            ang = (ang + rot) % 360
            pins[p["num"]] = (x + rx, y - ry, ang, p["name"])
        return pins

    def ref(self, prefix):
        self.refcount[prefix] = self.refcount.get(prefix, 0) + 1
        return f"{prefix}{self.refcount[prefix]}"

    def part(self, lib_id, x, y, prefix, value, footprint, nets, lcsc="", mirror=False,
             hide_value=False, pin_text=None):
        """Place a part and attach nets: nets = {pin_number: net_name | 'NC'}."""
        ref = self.ref(prefix)
        fields = {"LCSC": lcsc} if lcsc else {}
        pins = self._place(lib_id, x, y, ref, value, footprint, mirror=mirror, fields=fields,
                           hide_value=hide_value)
        for num, (px, py, ang, _name) in pins.items():
            net = nets.get(num)
            if net is None:
                raise ValueError(f"{ref} pin {num} not assigned")
            self.connect(px, py, ang, net)
            if pin_text and num in pin_text:
                # functional pin name, drawn on the other side of the connector body
                d = 1 if ang in (0.0,) else -1  # pin points right -> body is to the right
                tx = px + d * 9.0
                self.items.append(S("text", pin_text[num], S("exclude_from_sim", Sym("no")),
                                    S("at", tx, py, 0),
                                    S("effects", S("font", S("size", 1.0, 1.0)),
                                      S("justify", Sym("left" if d > 0 else "right"))),
                                    S("uuid", uid())))
        return ref

    def connect(self, x, y, ang, net):
        if net == "NC":
            self.items.append(S("no_connect", S("at", x, y), S("uuid", uid())))
            return
        # outward direction = opposite of pin angle (pin angle points into the body)
        dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(round(ang)) % 360]
        ex, ey = x + dx * STUB, y + dy * STUB
        self.items.append(S("wire", S("pts", S("xy", x, y), S("xy", ex, ey)),
                            S("stroke", S("width", 0), S("type", Sym("default"))), S("uuid", uid())))
        if net in POWER_NETS:
            self.power(net, ex, ey, (dx, dy))
        else:
            la = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(dx, dy)]
            just = "left" if la in (0, 90) else "right"
            self.items.append(S("label", net, S("at", ex, ey, la),
                                S("effects", S("font", S("size", 1.27, 1.27)),
                                  S("justify", Sym(just), Sym("bottom"))),
                                S("uuid", uid())))

    def power(self, net, x, y, outward=(0, 1), flag=False):
        lib_id = "power:PWR_FLAG" if flag else POWER_NETS[net]
        natural = (0, 1) if (net == "GND" and not flag) else (0, -1)  # schematic coords, Y down
        rot_for = {natural: 0}
        # CCW rotation in Y-up lib space; in Y-down screen space (dx,dy)->(dy,-dx) is +90
        v = natural
        for r in (90, 180, 270):
            v = (v[1], -v[0])
            rot_for[v] = r
        rot = rot_for.get(tuple(outward), 0)
        self.pwrcount += 1
        ref = f"#FLG{self.pwrcount:02d}" if flag else f"#PWR{self.pwrcount:02d}"
        self._place(lib_id, x, y, ref, "PWR_FLAG" if flag else net, rot=rot)

    def text(self, s, x, y, size=1.27, bold=False):
        font = S("font", S("size", size, size))
        if bold:
            font.append(S("bold", Sym("yes")))
        self.items.append(S("text", s, S("exclude_from_sim", Sym("no")), S("at", x, y, 0),
                            S("effects", font, S("justify", Sym("left"))), S("uuid", uid())))

    def box(self, x1, y1, x2, y2, title):
        self.items.append(S("rectangle", S("start", x1, y1), S("end", x2, y2),
                            S("stroke", S("width", 0), S("type", Sym("dash"))),
                            S("fill", S("type", Sym("none"))), S("uuid", uid())))
        self.text(title, x1 + 1.27, y1 + 3.0, 1.8, bold=True)

    def write(self, path, title, rev, date, comments):
        tb = S("title_block", S("title", title), S("date", date), S("rev", rev),
               S("company", "Balcony Irrigation Project"))
        for i, c in enumerate(comments, 1):
            tb.append(S("comment", i, c))
        doc = S("kicad_sch", S("version", 20250114), S("generator", "eeschema"),
                S("generator_version", "9.0"), S("uuid", self.root_uuid), S("paper", "A3"), tb,
                [Sym("lib_symbols")] + list(self.lib_symbols.values()))
        doc += self.items
        doc.append(S("sheet_instances", S("path", "/", S("page", "1"))))
        doc.append(S("embedded_fonts", Sym("no")))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(dump(doc) + "\n")


# --------------------------------------------------------------------------- circuit
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
FP_SOT23 = "Package_TO_SOT_SMD:SOT-23"
FP_SMA = "Diode_SMD:D_SMA"
FP_TB2 = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"
FP_XH = "Connector_JST:JST_XH_B{n}B-XH-A_1x{n:02d}_P2.50mm_Vertical"
FP_SOCK19 = "Connector_PinSocket_2.54mm:PinSocket_1x19_P2.54mm_Vertical"

# JLCPCB basic parts (verify before ordering)
LCSC = {"10k": "C25804", "100R": "C22775", "1k": "C21190", "4k7": "C23162",
        "100n": "C14663", "AO3400A": "C20917", "AO3401A": "C15127", "SS14": "C2480",
        "LED_G": "C72043"}

# ESP32-DevKitC V4 (38 pin, ESP32-WROOM-32/32E). Row spacing 25.4 mm.
# pin -> (function label shown on schematic, net)
DEVKIT_LEFT = {
    1: ("3V3", "+3V3"), 2: ("EN", "NC"), 3: ("IO36/VP", "SENS5"), 4: ("IO39/VN", "TANK"),
    5: ("IO34", "SENS3"), 6: ("IO35", "SENS4"), 7: ("IO32", "SENS1"), 8: ("IO33", "SENS2"),
    9: ("IO25", "PUMP4"), 10: ("IO26", "PUMP5"), 11: ("IO27", "LED_STATUS"), 12: ("IO14", "NC"),
    13: ("IO12", "NC"), 14: ("GND", "GND"), 15: ("IO13", "EXP_IO13"), 16: ("SD2", "NC"),
    17: ("SD3", "NC"), 18: ("CMD", "NC"), 19: ("5V", "+5V"),
}
DEVKIT_RIGHT = {
    1: ("GND", "GND"), 2: ("IO23", "PUMP3"), 3: ("IO22", "SCL"), 4: ("TX0", "NC"),
    5: ("RX0", "NC"), 6: ("IO21", "SDA"), 7: ("GND", "GND"), 8: ("IO19", "PUMP2"),
    9: ("IO18", "PUMP1"), 10: ("IO5", "NC"), 11: ("IO17", "EXP_IO17"), 12: ("IO16", "EXP_IO16"),
    13: ("IO4", "EXP_IO4"), 14: ("IO0", "NC"), 15: ("IO2", "NC"), 16: ("IO15", "NC"),
    17: ("SD1", "NC"), 18: ("SD0", "NC"), 19: ("CLK", "NC"),
}


def build():
    s = Schematic()
    R, C = "Device:R", "Device:C"

    # ---- power input --------------------------------------------------------------
    s.box(15, 20, 175, 95, "Stromversorgung 5 V (>= 2 A)")
    s.part("Connector:Barrel_Jack", 30, 50, "J", "5V DC 5.5/2.1",
           "Connector_BarrelJack:BarrelJack_Horizontal", {"1": "VIN_RAW", "2": "GND"})
    s.part("Connector:Screw_Terminal_01x02", 30, 75, "J", "5V DC (alt.)", FP_TB2,
           {"1": "VIN_RAW", "2": "GND"})
    s.part("Device:Polyfuse", 65, 50, "F", "PTC 2A hold", "Fuse:Fuse_1812_4532Metric",
           {"1": "VIN_RAW", "2": "VIN_FUSED"})
    q = s.part("Transistor_FET:AO3401A", 95, 50, "Q", "AO3401A", FP_SOT23,
               {"1": "GATE_REV", "2": "+5V", "3": "VIN_FUSED"}, LCSC["AO3401A"])
    s.part(R, 95, 75, "R", "10k", FP_R, {"1": "GATE_REV", "2": "GND"}, LCSC["10k"])
    s.part("Device:C_Polarized", 125, 60, "C", "1000uF 16V",
           "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm", {"1": "+5V", "2": "GND"})
    s.part(C, 140, 60, "C", "100nF", FP_C, {"1": "+5V", "2": "GND"}, LCSC["100n"])
    s.power("+5V", 155, 45, (0, -1), flag=True)
    s.power("+5V", 155, 45, (0, 1))
    s.power("GND", 170, 45, (0, -1), flag=True)
    s.power("GND", 170, 45, (0, 1))
    s.power("+3V3", 155, 80, (0, -1), flag=True)
    s.power("+3V3", 155, 80, (0, 1))
    s.text(f"{q}: Verpolschutz (P-MOSFET, high-side). F1: rueckstellende Sicherung.", 20, 90)

    # ---- ESP32 DevKitC -------------------------------------------------------------
    s.box(185, 20, 300, 130, "ESP32-DevKitC V4 (WROOM-32), steckbar")
    s.part("Connector_Generic:Conn_01x19", 215, 75, "J", "DevKit links", FP_SOCK19,
           {str(k): v[1] for k, v in DEVKIT_LEFT.items()},
           pin_text={str(k): v[0] for k, v in DEVKIT_LEFT.items()})
    s.part("Connector_Generic:Conn_01x19", 272, 75, "J", "DevKit rechts", FP_SOCK19,
           {str(k): v[1] for k, v in DEVKIT_RIGHT.items()}, mirror=True,
           pin_text={str(k): v[0] for k, v in DEVKIT_RIGHT.items()})
    s.text("Buchsenleisten 1x19, Reihenabstand 25,4 mm. 3V3 kommt vom DevKit-Regler.", 188, 125)

    # ---- status LED / I2C / tank / expansion ------------------------------------------
    s.box(310, 20, 405, 130, "Peripherie")
    s.part(R, 320, 40, "R", "1k", FP_R, {"1": "LED_STATUS", "2": "LED_A"}, LCSC["1k"])
    s.part("Device:LED", 335, 40, "D", "LED gruen", "LED_SMD:LED_0603_1608Metric",
           {"1": "GND", "2": "LED_A"}, LCSC["LED_G"])
    s.part("Connector_Generic:Conn_01x04", 368, 40, "J", "I2C (GND,3V3,SCL,SDA)",
           FP_XH.format(n=4), {"1": "GND", "2": "+3V3", "3": "SCL", "4": "SDA"})
    s.part(R, 388, 35, "R", "4k7", FP_R, {"1": "+3V3", "2": "SCL"}, LCSC["4k7"])
    s.part(R, 400, 35, "R", "4k7", FP_R, {"1": "+3V3", "2": "SDA"}, LCSC["4k7"])
    s.part("Connector_Generic:Conn_01x02", 325, 80, "J", "Tank leer (Schwimmer)",
           FP_XH.format(n=2), {"1": "TANK_SW", "2": "GND"})
    s.part(R, 345, 80, "R", "1k", FP_R, {"1": "TANK_SW", "2": "TANK"}, LCSC["1k"])
    s.part(R, 360, 75, "R", "10k", FP_R, {"1": "+3V3", "2": "TANK"}, LCSC["10k"])
    s.part(C, 375, 80, "C", "100nF", FP_C, {"1": "TANK", "2": "GND"}, LCSC["100n"])
    s.part("Connector_Generic:Conn_01x06", 330, 112, "J", "Erweiterung",
           "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
           {"1": "+3V3", "2": "GND", "3": "EXP_IO4", "4": "EXP_IO13", "5": "EXP_IO16",
            "6": "EXP_IO17"})
    for i, x in enumerate((360, 372, 384, 396)):
        s.part("Mechanical:MountingHole", x, 112, "H", "M3", "MountingHole:MountingHole_3.2mm_M3", {},
               hide_value=True)

    # ---- pump channels ------------------------------------------------------------
    s.box(15, 133, 405, 197, "Pumpenkanaele 1-5 (5 V, low-side Logic-Level-MOSFET)")
    for k in range(1, 6):
        x0 = 20 + (k - 1) * 78
        s.part(R, x0 + 10, 160, "R", "100", FP_R, {"1": f"PUMP{k}", "2": f"GATE{k}"}, LCSC["100R"])
        s.part(R, x0 + 22, 178, "R", "10k", FP_R, {"1": f"GATE{k}", "2": "GND"}, LCSC["10k"])
        s.part("Transistor_FET:AO3400A", x0 + 37, 160, "Q", "AO3400A", FP_SOT23,
               {"1": f"GATE{k}", "2": "GND", "3": f"PUMP{k}_N"}, LCSC["AO3400A"])
        s.part("Diode:SS14", x0 + 52, 150, "D", "SS14", FP_SMA,
               {"1": "+5V", "2": f"PUMP{k}_N"}, LCSC["SS14"])
        s.part("Connector:Screw_Terminal_01x02", x0 + 62, 175, "J", f"Pumpe {k}", FP_TB2,
               {"1": "+5V", "2": f"PUMP{k}_N"})

    # ---- sensor channels ----------------------------------------------------------
    s.box(15, 202, 405, 254, "Bodenfeuchtesensoren 1-5 (kapazitiv, 3,3 V, ADC1)")
    for k in range(1, 6):
        x0 = 20 + (k - 1) * 78
        s.part("Connector_Generic:Conn_01x03", x0 + 15, 225, "J", f"Sensor {k}",
               FP_XH.format(n=3), {"1": "GND", "2": "+3V3", "3": f"SENS{k}_RAW"})
        s.part(R, x0 + 35, 225, "R", "1k", FP_R, {"1": f"SENS{k}_RAW", "2": f"SENS{k}"}, LCSC["1k"])
        s.part(C, x0 + 50, 230, "C", "100nF", FP_C, {"1": f"SENS{k}", "2": "GND"}, LCSC["100n"])
    s.text("Steckerbelegung wie am Sensor: GND / VCC / AOUT. RC-Tiefpass 1k/100nF gegen Pumpenstoerungen.",
           20, 249)
    return s


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    s = build()
    sch = os.path.join(out, PROJECT + ".kicad_sch")
    s.write(sch, "Balkonbewaesserung v2 - Steuerplatine", "0.1", "2026-11-05",
            ["ESP32-DevKitC V4, 5x Pumpe, 5x Bodenfeuchte, Tank-Schwimmer, I2C",
             "Generiert mit hardware/v2/gen_schematic.py - nicht von Hand editieren"])
    pro = os.path.join(out, PROJECT + ".kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", newline="\n") as f:
            f.write('{"meta": {"filename": "%s.kicad_pro", "version": 1}}\n' % PROJECT)
    for fp in sorted(set(s.footprints_missing)):
        print("WARNING: footprint not found:", fp)
    print("wrote", sch)


if __name__ == "__main__":
    main()
