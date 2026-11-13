#!/usr/bin/env -S uv run --python 3.13
# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["bpy==5.3.*", "numpy"]
# ///
"""Cut a moving part (a hammer, a trigger) out of model.glb into its own node.

    game-part.py <asset dir> <Part> --y MIN MAX --z-above Z

Faces whose centre lies in the box (Blender axes: Y along the barrel, Z up)
become a child object named <Part>, with its origin at the bottom-centre of
the box so code can rotate it about its base. The box is kept in asset.json
under "parts", so a rerun of game-clean.py can be followed by this again.
Find the box with --probe, which prints the mesh height along the barrel.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import bpy
import bmesh  # noqa: E402  the bpy wheel provides it only after bpy loads
import numpy as np
from mathutils import Vector



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("asset", type=Path, help="folder holding model.glb and asset.json")
    ap.add_argument("part", nargs="?")
    ap.add_argument("--y", type=float, nargs=2)
    ap.add_argument("--z-above", type=float)
    ap.add_argument("--probe", action="store_true", help="print the top and bottom of the mesh in 30 slices along Y")
    a = ap.parse_args()
    folder = a.asset.resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(folder / "model.glb"))
    body = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    if a.probe:
        p = np.array([body.matrix_world @ v.co for v in body.data.vertices])
        edges = np.linspace(p[:, 1].min(), p[:, 1].max(), 31)
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (p[:, 1] >= lo) & (p[:, 1] < hi)
            if m.any():
                print(f"y {lo:+.3f}..{hi:+.3f}  z top {p[m, 2].max():+.3f}  bottom {p[m, 2].min():+.3f}")
        return
    if not (a.part and a.y and a.z_above is not None):
        raise SystemExit("give a part name, --y MIN MAX and --z-above Z, or --probe")
    bm = bmesh.new()
    bm.from_mesh(body.data)
    picked = [f for f in bm.faces if a.y[0] <= f.calc_center_median().y <= a.y[1] and f.calc_center_median().z >= a.z_above]
    if not picked:
        raise SystemExit("no faces in the box")
    src_col = bm.loops.layers.float_color.active or bm.loops.layers.color.active
    part_bm = bmesh.new()
    dst_col = part_bm.loops.layers.float_color.new("Col")
    vmap = {}
    for f in picked:
        verts = []
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = part_bm.verts.new(v.co)
            verts.append(vmap[v.index])
        nf = part_bm.faces.new(verts)
        for lo, ln in zip(f.loops, nf.loops):
            ln[dst_col] = lo[src_col]
    pivot = Vector((0.0, (a.y[0] + a.y[1]) / 2, a.z_above))
    bmesh.ops.translate(part_bm, verts=part_bm.verts[:], vec=-pivot)
    bmesh.ops.delete(bm, geom=picked, context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()
    me = bpy.data.meshes.new(a.part)
    part_bm.to_mesh(me)
    part_bm.free()
    part = bpy.data.objects.new(a.part, me)
    part.location = pivot
    bpy.context.scene.collection.objects.link(part)
    part.parent = body
    for o in (body, part):
        for p in o.data.polygons:
            p.use_smooth = False
    bpy.ops.export_scene.gltf(filepath=str(folder / "model.glb"), export_format="GLB", export_vertex_color="ACTIVE",
                              export_yup=True, export_extras=False)
    m = json.loads((folder / "asset.json").read_text())
    m.setdefault("parts", {})[a.part] = {"y": a.y, "z_above": a.z_above, "faces": len(picked),
                                         "pivot": [round(c, 4) for c in pivot]}
    (folder / "asset.json").write_text(json.dumps(m, indent=2) + "\n")
    print(a.part, len(picked), "faces, pivot", [round(c, 4) for c in pivot])


if __name__ == "__main__":
    main()
