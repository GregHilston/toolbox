#!/usr/bin/env -S uv run --python 3.13
# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["bpy==5.3.*", "numpy"]
# ///
"""Render a glb from four sides onto one sheet for review.

    game-turntable.py <asset dir> [--file model.glb] [--out turntable.png] [--grey]

Blender Workbench with studio lighting and the model's vertex colours, so the
sheet shows the shape; Workbench renders colours a little duller than they
are, so judge colour from the palette in asset.json.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

VIEWS = (("side", 90, 0), ("three-quarter", 35, 20), ("back side", -90, 0), ("top", 90, 70))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("asset", type=Path, help="folder holding the glb")
    ap.add_argument("--file", default="model.glb")
    ap.add_argument("--out", default="turntable.png")
    ap.add_argument("--grey", action="store_true", help="ignore colours, to compare shapes")
    a = ap.parse_args()
    folder = a.asset.resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(folder / a.file))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    pts = np.concatenate([np.array([o.matrix_world @ v.co for v in o.data.vertices]) for o in meshes])
    centre = Vector(((pts.max(0) + pts.min(0)) / 2).tolist())
    radius = float(np.linalg.norm(pts.max(0) - pts.min(0))) / 2

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.view_settings.view_transform = "Standard"  # AgX, the default, desaturates the palette
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "SINGLE" if a.grey else "VERTEX"
    shading.single_color = (0.7, 0.7, 0.7)
    shading.show_object_outline = True
    scene.world = bpy.data.worlds.new("bg")
    scene.render.film_transparent = False
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.45, 0.45, 0.45)
    scene.render.resolution_x = scene.render.resolution_y = 512

    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = radius * 2.3
    scene.collection.objects.link(cam)
    scene.camera = cam

    tiles = []
    for name, yaw, pitch in VIEWS:
        y, p = math.radians(yaw), math.radians(pitch)
        offset = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * radius * 4
        cam.location = centre + offset
        cam.rotation_euler = (centre - cam.location).to_track_quat("-Z", "Y").to_euler()
        path = folder / f".tt-{name.replace(' ', '-')}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        tiles.append(path)

    img = bpy.data.images
    sheet = np.zeros((512, 512 * len(tiles), 4), dtype=np.float32)
    for i, t in enumerate(tiles):
        im = img.load(str(t))
        px = np.array(im.pixels[:], dtype=np.float32).reshape(512, 512, 4)
        sheet[:, i * 512:(i + 1) * 512] = px
        t.unlink()
    out = img.new("sheet", 512 * len(tiles), 512, alpha=True)
    out.pixels = sheet.ravel()
    out.filepath_raw = str(folder / a.out)
    out.file_format = "PNG"
    out.save()
    print(folder / a.out)


if __name__ == "__main__":
    main()
