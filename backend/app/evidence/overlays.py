"""Overlays: pixels that do not change across shot boundaries cannot belong to either shot. Pixels steady over the
whole reel (with at least two shots), minus text boxes, form connected regions: each is an overlay slot. A thin
region is a bar, a border-shaped one a frame, the rest stickers or logos (the video AI describes them).
Stickers and logos are content, not structure: the template keeps where, when and what kind, never the graphic.
shortcut: only overlays present for the whole reel are found; a sticker on screen for part of it needs per-window
stability (upgrade when the gold set shows them)."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load

NAME, VERSION, DEPS = "overlays", 1, ["cuts", "transitions", "text"]
STEADY = 6.0  # temporal std (0..255, max over RGB) below which a pixel never changes
MIN_AREA = 0.002  # share of the frame
THIN = 0.03  # a region thinner than this (share of the side) is a bar
FRAME_FILL = 0.35  # a region filling less than this of its bounding box is a frame / border


def run(ctx) -> list[ir.Item]:
    _, rgb = load(ctx.key)
    rgb = np.asarray(rgb)
    n, h, w, _ = rgb.shape
    if len(boundaries(ctx.ev)) < 1:  # one shot: a static background is indistinguishable from an overlay
        return []
    steady = rgb.astype(np.float32).std(axis=0).max(axis=2) < STEADY
    for t in ctx.ev.get("text", []):  # captions are steady too; they have their own track
        b = t.data["box"]
        steady[int(b["y"] * h) - 1:int((b["y"] + b["h"]) * h) + 2, int(b["x"] * w) - 1:int((b["x"] + b["w"]) * w) + 2] = False
    mask = cv2.morphologyEx(steady.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
    items = []
    for c in range(1, count):
        x, y, bw, bh, area = stats[c]
        if area < MIN_AREA * w * h or (bw >= w - 1 and bh >= h - 1):
            continue
        fill = area / max(1, bw * bh)
        kind = "frame" if fill < FRAME_FILL else "shape" if min(bw / w, bh / h) < THIN else "sticker"
        colour = rgb[0][lab == c].mean(axis=0)
        items.append(ir.Item(id=f"overlays_{len(items)}", track=NAME, start=0, end=n, conf=0.6, tool="cross-cut stability",
                             data={"kind": kind, "box": ir.Box(x=x / w, y=y / h, w=bw / w, h=bh / h).model_dump(),
                                   "fill": round(float(fill), 3), "colour": "#{:02X}{:02X}{:02X}".format(*map(int, colour))}))
    return items
