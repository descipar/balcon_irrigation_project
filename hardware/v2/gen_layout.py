#!/usr/bin/env python3
"""Generate and autoroute the PCB for the balcony irrigation controller v2.

Needs KiCad 9 (pcbnew Python module, kicad-cli) and Freerouting:

    python3 gen_layout.py kicad/balcon_irrigation_v2.kicad_sch [--freerouting PATH.jar]

Steps: netlist from schematic -> place footprints (positions in PLACEMENT) ->
board outline, GND pours, text -> Specctra DSN -> Freerouting -> SES import ->
zone fill -> save .kicad_pcb (+ net classes in .kicad_pro).
"""
import argparse
import json
import os
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_schematic import parse, find  # noqa: E402  (same s-expression helpers)

KICAD = os.environ.get("KICAD_SHARE", "/usr/share/kicad")
FPDIR = os.path.join(KICAD, "footprints")
MM = pcbnew.FromMM

BOARD_W, BOARD_H = 100.0, 100.0

# ---------------------------------------------------------------- net classes
NETCLASSES = {
    # name: (track, clearance, via_diameter, via_drill)
    "Default": (0.25, 0.2, 0.6, 0.3),
    "Power": (0.8, 0.25, 0.8, 0.4),
    "Ground": (0.5, 0.25, 0.8, 0.4),
}
NETCLASS_PATTERNS = [
    ("Ground", "GND"),
    ("Power", "+5V"),
    ("Power", "/VIN_*"),
    ("Power", "/PUMP?_N"),
]

# ---------------------------------------------------------------- placement
# ref: (x, y, rotation_deg)   origin top-left, y down, mm
PUMP_X = [11, 24, 37, 50, 63]          # pad 1 of the pump terminals
SENS_X = [12, 23.5, 35, 46.5, 58]      # pad 1 of the sensor connectors


def placement():
    p = {
        # power input (left edge)
        "J1": (14, 30, 0),          # barrel jack, opening towards left edge
        "J2": (5.5, 48, 270),       # screw terminal, wire entry towards left edge
        "F1": (22, 30, 0),
        "Q1": (29, 30, 0),
        "R1": (29, 35, 90),
        "C1": (19, 58, 0),          # 1000uF THT
        "C2": (33, 40, 90),
        # ESP32 DevKitC: pin 1 (antenna end) on the right, USB on the left
        "J3": (91, 32, 270),        # 3V3 ... 5V row
        "J4": (91, 57.4, 270),      # GND ... CLK row
        # status LED
        "R2": (40, 24, 0),
        "D1": (45, 24, 180),
        # top edge: sensors, tank, I2C
        "J6": (69.5, 5, 0),          # tank float switch
        "R5": (70.5, 13, 90),
        "R6": (73, 13, 90),
        "C3": (75.5, 13, 90),
        "J5": (81.5, 5, 0),          # I2C
        "R3": (84, 13, 90),
        "R4": (87, 13, 90),
        # expansion header
        "J7": (96, 66, 0),
        # mounting holes
        "H1": (4, 4, 0), "H2": (96, 4, 0), "H3": (4, 96, 0), "H4": (96, 96, 0),
    }
    # sensors J13..J17, R17..R21, C4..C8
    for k in range(5):
        x = SENS_X[k]
        p[f"J{13 + k}"] = (x, 5, 0)
        p[f"R{17 + k}"] = (x + 1, 14, 90)
        p[f"C{4 + k}"] = (x + 4, 14, 90)
    # pumps: J8..J12, Q2..Q6, D2..D6, Rgate R7,9,11,13,15, Rpull R8,10,12,14,16
    for k in range(5):
        x = PUMP_X[k]
        p[f"J{8 + k}"] = (x, 94.5, 0)
        p[f"R{7 + 2 * k}"] = (x - 1, 75, 90)
        p[f"R{8 + 2 * k}"] = (x + 2, 75, 90)
        p[f"Q{2 + k}"] = (x + 2.5, 80.5, 0)
        p[f"D{2 + k}"] = (x + 3, 86, 0)
    return p


SILK = [
    # text, x, y, size, rotation
    ("BALKONBEWAESSERUNG v2", 50, 70, 1.5, 0),
    ("SENSOR 1", SENS_X[0] + 2.5, 9.8, 0.8, 0),
    ("SENSOR 2", SENS_X[1] + 2.5, 9.8, 0.8, 0),
    ("SENSOR 3", SENS_X[2] + 2.5, 9.8, 0.8, 0),
    ("SENSOR 4", SENS_X[3] + 2.5, 9.8, 0.8, 0),
    ("SENSOR 5", SENS_X[4] + 2.5, 9.8, 0.8, 0),
    ("TANK", 70.75, 9.8, 0.8, 0),
    ("I2C", 85.25, 9.8, 0.8, 0),
    ("5V IN", 7, 22.5, 1.0, 0),
    ("+", 12.5, 48, 1.5, 0),
    ("-", 12.5, 53.08, 1.5, 0),
    ("ESP32-DevKitC V4: USB <- links, Antenne -> rechts", 68, 61.5, 1.0, 0),
    ("EXP", 96, 81, 0.8, 0),
]
for _k in range(5):
    SILK.append((f"PUMPE {_k + 1}", PUMP_X[_k] + 2.54, 99, 0.8, 0))


# ---------------------------------------------------------------- helpers
def export_netlist(sch, out):
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", out, sch],
                   check=True, stdout=subprocess.DEVNULL)
    root = parse(open(out, encoding="utf-8").read())
    comps = {}
    for c in find(find(root, "components")[0], "comp"):
        ref = find(c, "ref")[0][1]
        comps[ref] = {"value": find(c, "value")[0][1],
                      "footprint": find(c, "footprint")[0][1] if find(c, "footprint") else ""}
    pad_net = {}
    for n in find(find(root, "nets")[0], "net"):
        name = find(n, "name")[0][1]
        for node in find(n, "node"):
            pad_net[(find(node, "ref")[0][1], find(node, "pin")[0][1])] = name
    return comps, pad_net


def add_line(board, x1, y1, x2, y2, layer=pcbnew.Edge_Cuts, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
    s.SetLayer(layer)
    s.SetWidth(MM(width))
    board.Add(s)


def add_zone(board, net, layer, pts, keepout=False):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    poly = z.Outline()
    poly.NewOutline()
    for x, y in pts:
        poly.Append(MM(x), MM(y))
    if keepout:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
    else:
        z.SetNet(net)
        z.SetLocalClearance(MM(0.3))
        z.SetMinThickness(MM(0.25))
        z.SetThermalReliefGap(MM(0.4))
        z.SetThermalReliefSpokeWidth(MM(0.5))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)  # SMD pads solid
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)


def add_text(board, text, x, y, size, rot):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetTextAngleDegrees(rot)
    board.Add(t)


def write_project(pro_path):
    """Net classes + design rules live in the .kicad_pro in KiCad 9."""
    pro = {}
    if os.path.exists(pro_path):
        try:
            pro = json.load(open(pro_path))
        except ValueError:
            pro = {}
    classes = []
    for name, (tw, cl, vd, vdr) in NETCLASSES.items():
        classes.append({
            "name": name, "track_width": tw, "clearance": cl, "via_diameter": vd, "via_drill": vdr,
            "microvia_diameter": 0.3, "microvia_drill": 0.1, "diff_pair_width": 0.2,
            "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25, "wire_width": 6, "bus_width": 12,
            "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
            "schematic_color": "rgba(0, 0, 0, 0.000)",
            "priority": 2147483647 if name == "Default" else 0,
        })
    pro["net_settings"] = {
        "classes": classes, "meta": {"version": 4}, "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [{"netclass": c, "pattern": p} for c, p in NETCLASS_PATTERNS],
    }
    # JLCPCB standard 2-layer capabilities (with some margin)
    pro.setdefault("board", {}).setdefault("design_settings", {})["rules"] = {
        "min_clearance": 0.2, "min_track_width": 0.15, "min_via_annular_width": 0.13,
        "min_via_diameter": 0.5, "min_through_hole_diameter": 0.3, "min_hole_to_hole": 0.25,
        "min_hole_clearance": 0.25, "min_copper_edge_clearance": 0.5, "min_silk_clearance": 0.0,
        "min_text_height": 0.6, "min_text_thickness": 0.1, "solder_mask_to_copper_clearance": 0.0,
    }
    pro.setdefault("meta", {})["filename"] = os.path.basename(pro_path)
    with open(pro_path, "w", newline="\n") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------- main
def build_board(sch, pcb_path):
    base = os.path.splitext(pcb_path)[0]
    comps, pad_net = export_netlist(sch, base + ".net")
    board = pcbnew.NewBoard(pcb_path)
    board.SetCopperLayerCount(2)

    nets = {}
    for name in sorted(set(pad_net.values())):
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n

    place = placement()
    missing = sorted(set(comps) - set(place))
    if missing:
        raise SystemExit(f"no placement for: {missing}")
    for ref, c in sorted(comps.items()):
        lib, name = c["footprint"].split(":")
        fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), name)
        if fp is None:
            raise SystemExit(f"footprint not found: {c['footprint']}")
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        x, y, rot = place[ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.SetOrientationDegrees(rot)
        fp.Value().SetVisible(False)
        refd = fp.Reference()
        refd.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        refd.SetTextThickness(MM(0.12))
        if ref.startswith("H"):
            refd.SetVisible(False)
        for pad in fp.Pads():
            net = pad_net.get((ref, pad.GetNumber()))
            if net in nets:
                pad.SetNet(nets[net])

    # outline with 2 mm corner radius
    r = 2.0
    W, H = BOARD_W, BOARD_H
    add_line(board, r, 0, W - r, 0)
    add_line(board, W, r, W, H - r)
    add_line(board, W - r, H, r, H)
    add_line(board, 0, H - r, 0, r)
    for cx, cy, sx, sy in ((r, r, 0, r), (W - r, r, W - r, 0), (W - r, H - r, W, H - r), (r, H - r, r, H)):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        a.SetStart(pcbnew.VECTOR2I(MM(sx), MM(sy)))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(MM(0.1))
        board.Add(a)

    # no copper pour under the ESP32 antenna (module overhangs pin 1 to the right)
    add_zone(board, None, pcbnew.F_Cu, [(87, 27), (W, 27), (W, 63), (87, 63)], keepout=True)

    for t in SILK:
        add_text(board, *t)

    board.Save(pcb_path)
    write_project(base + ".kicad_pro")


def route(pcb_path, jar, passes):
    base = os.path.splitext(pcb_path)[0]
    board = pcbnew.LoadBoard(pcb_path)
    ns = board.GetDesignSettings().m_NetSettings
    for net in ("+5V", "GND", "/PUMP1_N", "/SENS1"):
        print(f"  netclass {net}: {ns.GetEffectiveNetClass(net).GetName()}")
    dsn, ses = base + ".dsn", base + ".ses"
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("DSN export failed")
    subprocess.run(["java", "-jar", jar, "-de", dsn, "-do", ses, "-mp", str(passes),
                    "--gui.enabled=false"], check=True)
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit("SES import failed")
    # GND pours only after routing, so the router lays real GND tracks instead of
    # relying on a plane that may not reach every pad
    gnd = board.FindNet("GND")
    outline = [(0.3, 0.3), (BOARD_W - 0.3, 0.3), (BOARD_W - 0.3, BOARD_H - 0.3), (0.3, BOARD_H - 0.3)]
    add_zone(board, gnd, pcbnew.B_Cu, outline)
    add_zone(board, gnd, pcbnew.F_Cu, outline)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(pcb_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sch")
    ap.add_argument("--freerouting", default=os.path.expanduser("~/tools/freerouting/freerouting-2.5.0.jar"))
    ap.add_argument("--passes", type=int, default=100)
    ap.add_argument("--no-route", action="store_true")
    a = ap.parse_args()
    pcb = os.path.splitext(a.sch)[0] + ".kicad_pcb"
    build_board(a.sch, pcb)
    print("placed:", pcb)
    if not a.no_route:
        route(pcb, a.freerouting, a.passes)
        print("routed:", pcb)


if __name__ == "__main__":
    main()
