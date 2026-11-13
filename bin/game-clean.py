#!/usr/bin/env -S uv run --python 3.13
# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["bpy==5.3.*", "numpy"]
# ///
"""Clean raw.glb into model.glb: weld, palette, decimate, orient, scale, export.

    game-clean.py <asset dir> --length METRES [--tris 1000] [--colours 4] [--flip]

1. Voxel remesh welds the image-to-3D tool's loose shells into one surface.
2. Each face takes the colour of the nearest raw face, snapped to a k-colour
   palette (k-means), stored as a face label.
3. Edges between labels are split, so decimation keeps every colour border
   as an edge instead of cutting through it (thin bands stay bands).
4. Collapse decimation to the triangle budget, then one flat colour per face.
5. Blender is Z up; the barrel goes along +Y, which the Y-up export turns into
   Godot's -Z. --flip turns it end for end. A Muzzle empty marks the front.

Writes model.glb and a "clean" block in asset.json.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import bpy
import bmesh  # noqa: E402  the bpy wheel provides it only after bpy loads
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree



def load(path: Path) -> bpy.types.Object:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return obj


def face_colours(obj) -> tuple[np.ndarray, np.ndarray]:
    """Centre and mean RGB of every face, from the first colour attribute."""
    me = obj.data
    centres = np.empty(len(me.polygons) * 3, dtype=np.float32)
    me.polygons.foreach_get("center", centres)
    if not me.color_attributes:  # a shape-only tool: one mid grey
        return centres.reshape(-1, 3), np.full((len(me.polygons), 3), 0.5)
    attr = me.color_attributes[0]
    vals = np.empty(len(attr.data) * 4, dtype=np.float32)
    attr.data.foreach_get("color", vals)
    vals = vals.reshape(-1, 4)[:, :3]
    if attr.domain == "POINT":
        idx = np.empty(len(me.loops), dtype=np.int64)
        me.loops.foreach_get("vertex_index", idx)
        vals = vals[idx]
    starts = np.empty(len(me.polygons), dtype=np.int64)
    counts = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_start", starts)
    me.polygons.foreach_get("loop_total", counts)
    return centres.reshape(-1, 3), np.add.reduceat(vals, starts) / counts[:, None]


def lab(rgb: np.ndarray) -> np.ndarray:
    """Linear RGB to CIE Lab (D65), where distance tracks what eyes see."""
    xyz = rgb @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def kmeans(x: np.ndarray, k: int, iters: int = 30) -> tuple[np.ndarray, np.ndarray]:
    centres = [x[0]]
    for _ in range(k - 1):  # farthest-point seeds, so one colour can't take two slots
        d = np.min([((x - c) ** 2).sum(1) for c in centres], axis=0)
        centres.append(x[np.argmax(d)])
    centres = np.array(centres)
    for _ in range(iters):
        label = np.argmin(((x[:, None, :] - centres[None]) ** 2).sum(-1), axis=1)
        for j in range(k):
            if (label == j).any():
                centres[j] = x[label == j].mean(0)
    return centres, label


def concept_palette(png: Path, k: int) -> tuple[np.ndarray, float]:
    """The concept's own colours in linear RGB, background excluded, and its mean Lab lightness.

    Image-to-3D darkens and shifts colours, so the model's clusters are
    renamed to the nearest concept colour before painting.
    """
    img = bpy.data.images.load(str(png))
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::4, ::4, :3].reshape(-1, 3) ** 2.2  # sRGB PNG; vertex colours are linear
    bg = np.median(np.concatenate([px[:w // 4], px[-w // 4:]]), axis=0)
    fg = px[np.abs(px - bg).max(1) > 0.06]
    _, label = kmeans(lab(fg), k + 2)
    centres = np.array([fg[label == j].mean(0) for j in range(k + 2) if (label == j).sum() > 0.01 * len(fg)])
    return centres, float(lab(fg)[:, 0].mean())


def match(model: np.ndarray, shares: np.ndarray, concept: np.ndarray, concept_l: float) -> np.ndarray:
    m = lab(model)
    m[:, 0] += concept_l - (m[:, 0] * shares).sum()  # else dark steel snaps to shadow
    d = ((m[:, None] - lab(concept)[None]) ** 2).sum(-1)
    return concept[np.argmin(d, axis=1)]


def remesh(obj, voxels: int) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.data.remesh_voxel_size = max(obj.dimensions) / voxels
    bpy.ops.object.voxel_remesh()


def label_faces(obj, src_centres: np.ndarray, src_rgb: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Palette index per face, from the nearest raw face; returns the palette and each colour's share of faces."""
    tree = KDTree(len(src_centres))
    for i, c in enumerate(src_centres):
        tree.insert(c, i)
    tree.balance()
    rgb = np.array([src_rgb[tree.find(p.center)[1]] for p in obj.data.polygons])
    _, label = kmeans(lab(rgb), k)
    palette = np.array([rgb[label == j].mean(0) if (label == j).any() else rgb[0] for j in range(k)])
    attr = obj.data.attributes.new("pal", "INT", "FACE")
    attr.data.foreach_set("value", label.astype(np.int32))
    return palette, np.bincount(label, minlength=k) / len(label)


def split_borders(obj, smooth: int) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    layer = bm.faces.layers.int["pal"]
    bm.faces.ensure_lookup_table()
    for _ in range(smooth):  # majority vote over edge neighbours removes speckle
        new = []
        for f in bm.faces:
            votes = [g[layer] for e in f.edges for g in e.link_faces if g is not f] + [f[layer]]
            new.append(max(set(votes), key=votes.count))
        for f, v in zip(bm.faces, new):
            f[layer] = v
    border = [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0][layer] != e.link_faces[1][layer]]
    bmesh.ops.split_edges(bm, edges=border)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()


def decimate(obj, tris: int) -> None:
    now = len(obj.data.polygons)
    if now > tris:
        mod = obj.modifiers.new("dec", "DECIMATE")
        mod.ratio = tris / now
        mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=mod.name)


def paint(obj, palette: np.ndarray) -> list[str]:
    """One flat palette colour per face, as the only (corner) colour attribute."""
    me = obj.data
    label = np.empty(len(me.polygons), dtype=np.int32)
    me.attributes["pal"].data.foreach_get("value", label)
    counts = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_total", counts)
    out = np.ones((len(me.loops), 4), dtype=np.float32)
    out[:, :3] = np.repeat(palette[label], counts, axis=0)
    for name in [a.name for a in me.color_attributes]:
        me.color_attributes.remove(me.color_attributes[name])
    me.attributes.remove(me.attributes["pal"])
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    attr.data.foreach_set("color", out.ravel())
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = me.color_attributes.active_color_index
    return ["#%02x%02x%02x" % tuple(int(round(255 * c ** (1 / 2.2))) for c in rgb) for rgb in palette]


def orient(obj, length: float, flip: bool) -> None:
    """Longest horizontal side along +Y, centred, scaled to `length` metres."""
    pts = np.array([v.co for v in obj.data.vertices])
    size = pts.max(0) - pts.min(0)
    axis = int(np.argmax(size[:2]))
    to_y = Matrix.Rotation(math.radians(90), 4, "Z") if axis == 0 else Matrix.Identity(4)
    if flip:
        to_y = Matrix.Rotation(math.pi, 4, "Z") @ to_y
    centre = Vector(((pts.max(0) + pts.min(0)) / 2).tolist())
    obj.data.transform(Matrix.Scale(length / size[axis], 4) @ to_y @ Matrix.Translation(-centre))
    obj.data.update()


def add_muzzle(obj) -> list[float]:
    """An empty at the centre of the front 2% of the mesh."""
    pts = np.array([v.co for v in obj.data.vertices])
    front = pts[pts[:, 1] >= pts[:, 1].max() - 0.02 * np.ptp(pts[:, 1])]
    at = front.mean(0)
    empty = bpy.data.objects.new("Muzzle", None)
    empty.location = Vector(at.tolist())
    bpy.context.scene.collection.objects.link(empty)
    empty.parent = obj
    return [round(float(c), 4) for c in at]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("asset", type=Path, help="folder holding raw.glb, concept.png and asset.json")
    ap.add_argument("--tris", type=int, default=1000)
    ap.add_argument("--colours", type=int, default=4)
    ap.add_argument("--smooth", type=int, default=3, help="label majority-vote passes")
    ap.add_argument("--voxels", type=int, default=200, help="remesh cells along the longest side")
    ap.add_argument("--length", type=float, required=True, help="real size of the longest side, in metres")
    ap.add_argument("--flip", action="store_true")
    ap.add_argument("--raw-colours", action="store_true", help="keep the 3D tool's colours, not the concept's")
    a = ap.parse_args()
    folder = a.asset.resolve()
    obj = load(folder / "raw.glb")
    obj.name = folder.name
    raw_tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    shape_only = not obj.data.color_attributes
    src_centres, src_rgb = face_colours(obj)
    if shape_only:
        a.colours, a.raw_colours = 1, True
    remesh(obj, a.voxels)
    palette, shares = label_faces(obj, src_centres, src_rgb, a.colours)
    if not a.raw_colours:
        palette = match(palette, shares, *concept_palette(folder / "concept.png", a.colours))
    split_borders(obj, a.smooth)
    decimate(obj, a.tris)
    hexes = paint(obj, palette)
    length = a.length
    orient(obj, length, a.flip)
    muzzle = add_muzzle(obj)
    for p in obj.data.polygons:
        p.use_smooth = False
    bpy.ops.export_scene.gltf(filepath=str(folder / "model.glb"), export_format="GLB", export_vertex_color="ACTIVE",
                              export_yup=True, export_apply=True, export_extras=False)
    manifest_path = folder / "asset.json"
    m = json.loads(manifest_path.read_text())
    m["clean"] = {"script": "game-clean.py", "blender": bpy.app.version_string, "raw_tris": raw_tris,
                  "tris": len(obj.data.polygons), "target_tris": a.tris, "voxels": a.voxels, "smooth": a.smooth, "colours_from": "none" if shape_only else "raw" if a.raw_colours else "concept",
                  "palette": sorted(set(hexes)),
                  "length_m": length, "flip": a.flip, "muzzle": muzzle}
    manifest_path.write_text(json.dumps(m, indent=2) + "\n")
    print(json.dumps(m["clean"]))


if __name__ == "__main__":
    main()
