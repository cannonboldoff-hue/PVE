"""Per-slot colour statistics (CIE Lab, OpenCV 8-bit scale: L 0..255, a/b centred on 128), text and overlay
regions masked out. They become the slot's ColourTarget; rendering moves a new clip's statistics toward them."""
import cv2
import numpy as np

from .. import ir
from . import boundaries
from .frames import load

NAME, VERSION, DEPS = "colour", 1, ["cuts", "transitions", "text", "overlays"]


def stats(rgb: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """rgb: (n, h, w, 3) uint8. Returns ColourTarget fields."""
    lab = cv2.cvtColor(rgb.reshape(-1, rgb.shape[-2], 3), cv2.COLOR_RGB2LAB).reshape(rgb.shape).astype(np.float32)
    hsv = cv2.cvtColor(rgb.reshape(-1, rgb.shape[-2], 3), cv2.COLOR_RGB2HSV).reshape(rgb.shape).astype(np.float32)
    m = np.broadcast_to(mask, rgb.shape[:3]) if mask is not None else np.ones(rgb.shape[:3], bool)
    if not m.any():  # text/overlay boxes cover the whole frame: use unmasked pixels rather than none
        m = np.ones(rgb.shape[:3], bool)
    L, A, B, S = lab[..., 0][m], lab[..., 1][m], lab[..., 2][m], hsv[..., 1][m]
    return {"l_mean": float(L.mean()), "l_std": float(L.std()), "a_mean": float(A.mean()), "a_std": float(A.std()),
            "b_mean": float(B.mean()), "b_std": float(B.std()), "saturation": float(S.mean() / 255),
            "contrast": float((np.percentile(L, 95) - np.percentile(L, 5)) / 255)}


def run(ctx) -> list[ir.Item]:
    _, rgb = load(ctx.key)
    rgb = np.asarray(rgb)
    n, h, w, _ = rgb.shape
    bs = boundaries(ctx.ev)
    edges = [0, *[f for f, _, _ in bs], n]
    items = []
    for k, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        mask = np.ones((h, w), bool)
        for i in [*ctx.ev.get("text", []), *ctx.ev.get("overlays", [])]:
            if i.start < b and i.end > a:
                bx = i.data["box"]
                mask[int(bx["y"] * h):int((bx["y"] + bx["h"]) * h) + 1, int(bx["x"] * w):int((bx["x"] + bx["w"]) * w) + 1] = False
        frames = rgb[a:b:max(1, (b - a) // 12)]  # a dozen frames per shot is plenty for means and spreads
        items.append(ir.Item(id=f"colour_{k}", track=NAME, start=a, end=b, conf=0.8, tool="opencv lab",
                             data=stats(frames, mask)))
    return items
