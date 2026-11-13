#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Turn an approved concept into raw.glb with TRELLIS.2 in moria's ComfyUI.

    game-model.py <asset dir> [--seed N] [--resolution 32|64] [--tool trellis|hunyuan]

Reads <asset dir>/concept.png, writes <asset dir>/raw.glb, and records the
tool, weights, settings, seed and time in asset.json under "model". Free and
local: TRELLIS.2, BiRefNet and the repacks are MIT, DINOv3 is Meta's
commercial-OK licence (notes vault: llm/ai-concept-art-pipeline.md). Runs the graph
of ComfyUI's own TRELLIS.2 template (3d_pixal3d_trellis2_image_to_model) up to
vertex colours (PaintMesh) and skips its texture bake: we bake to the palette.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

COMFY = os.environ.get("COMFY_URL", "http://moria.tail1b9d9.ts.net:8188")
MODELS = {
    "unet": "trellis_2_int8_convrot.safetensors",
    "shape_vae": "trellis_2_shape_vae_bf16.safetensors",
    "texture_vae": "trellis_2_texture_vae_bf16.safetensors",
    "dino": "dino_v3_L_naf_fp32.safetensors",
    "bg": "birefnet.safetensors",
}


MODEL_DIR = Path(os.environ.get("COMFY_MODELS", Path.home() / "ComfyUI" / "models"))
SUBDIR = {"unet": "diffusion_models", "shape_vae": "vae", "texture_vae": "vae", "dino": "clip_vision", "bg": "background_removal"}


def weight_hashes() -> dict:
    """SHA-256 of each weight file, for the asset's licence ledger."""
    out = {}
    for key, name in MODELS.items():
        h = hashlib.sha256()
        with open(MODEL_DIR / SUBDIR[key] / name, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        out[key] = h.hexdigest()
    return out


def call(path: str, body: bytes | None = None, ctype: str = "application/json") -> dict:
    req = urllib.request.Request(COMFY + path, data=body, headers={"Content-Type": ctype} if body else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def upload(png: Path) -> str:
    boundary = uuid.uuid4().hex
    name = f"lp-{png.parent.name}.png"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode()
        + png.read_bytes()
        + f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{boundary}--\r\n'.encode()
    )
    return call("/upload/image", body, f"multipart/form-data; boundary={boundary}")["name"]


def graph(image: str, seed: int, resolution: str, prefix: str) -> dict:
    """The template's TRELLIS.2 branch, its sampler settings unchanged, seeds offset from ours."""
    def ks(model, pos, neg, latent, s, steps, cfg, sched):
        return {"class_type": "KSampler", "inputs": {"model": model, "seed": s, "steps": steps, "cfg": cfg,
                "sampler_name": "euler", "scheduler": sched, "positive": pos, "negative": neg,
                "latent_image": latent, "denoise": 1.0}}
    return {
        "img": {"class_type": "LoadImage", "inputs": {"image": image}},
        "bgm": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": MODELS["bg"]}},
        "mask": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["bgm", 0], "image": ["img", 0]}},
        "crop": {"class_type": "ImageCropToMask", "inputs": {"images": ["img", 0], "masks": ["mask", 0], "width": 1024,
                 "height": 1024, "pad_factor": 1.1, "grow_mask": 0, "background": "#000000"}},
        "dino": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": MODELS["dino"]}},
        "cond": {"class_type": "Trellis2Conditioning", "inputs": {"clip_vision_model": ["dino", 0], "image": ["crop", 0]}},
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": MODELS["unet"], "weight_dtype": "default"}},
        "svae": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["shape_vae"]}},
        "tvae": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["texture_vae"]}},
        "cfg_s": {"class_type": "CFGOverride", "inputs": {"model": ["unet", 0], "cfg": 1, "start_percent": 0.667, "end_percent": 1}},
        "res_s": {"class_type": "RescaleCFG", "inputs": {"model": ["cfg_s", 0], "multiplier": 0.7}},
        "msd3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["res_s", 0], "shift": 5}},
        "cfg_h": {"class_type": "CFGOverride", "inputs": {"model": ["unet", 0], "cfg": 1, "start_percent": 0.769, "end_percent": 1}},
        "res_h": {"class_type": "RescaleCFG", "inputs": {"model": ["cfg_h", 0], "multiplier": 0.5}},
        "empty": {"class_type": "EmptyTrellis2LatentStructure", "inputs": {"batch_size": 1}},
        "k_struct": ks(["msd3", 0], ["cond", 0], ["cond", 1], ["empty", 0], seed, 12, 7.5, "normal"),
        "voxel": {"class_type": "VaeDecodeStructureTrellis2", "inputs": {"samples": ["k_struct", 0], "vae": ["svae", 0], "resolution": resolution}},
        "shape": {"class_type": "Trellis2ShapeStage", "inputs": {"positive": ["cond", 0], "negative": ["cond", 1], "voxel": ["voxel", 0]}},
        "k_shape": ks(["res_h", 0], ["shape", 0], ["shape", 1], ["shape", 2], seed + 1, 20, 7.5, "normal"),
        "up": {"class_type": "Trellis2UpsampleStage", "inputs": {"positive": ["shape", 0], "negative": ["shape", 1],
               "shape_latent": ["k_shape", 0], "vae": ["svae", 0], "target_resolution": 1536}},
        "k_up": ks(["res_h", 0], ["up", 0], ["up", 1], ["up", 2], seed + 2, 12, 7.5, "simple"),
        "mesh": {"class_type": "VaeDecodeShapeTrellis", "inputs": {"samples": ["k_up", 0], "vae": ["svae", 0]}},
        "tex": {"class_type": "Trellis2TextureStage", "inputs": {"positive": ["up", 0], "negative": ["up", 1], "shape_latent": ["k_up", 0]}},
        "k_tex": ks(["unet", 0], ["tex", 0], ["tex", 1], ["tex", 2], seed + 3, 12, 1, "normal"),
        "colors": {"class_type": "VaeDecodeTextureTrellis", "inputs": {"samples": ["k_tex", 0], "vae": ["tvae", 0], "shape_subdivides": ["mesh", 1]}},
        "dec": {"class_type": "DecimateMesh", "inputs": {"mesh": ["mesh", 0], "target_face_count": 200000, "placement_mode": "midpoint"}},
        "paint": {"class_type": "PaintMesh", "inputs": {"mesh": ["dec", 0], "voxel_colors": ["colors", 0]}},
        "save": {"class_type": "SaveGLB", "inputs": {"mesh": ["paint", 0], "filename_prefix": prefix}},
    }


HUNYUAN = "hunyuan_3d_v2.1.safetensors"


def hunyuan_graph(image: str, seed: int, prefix: str) -> dict:
    """ComfyUI's 3d_hunyuan3d-v2.1 template, with our background removal in front. Shape only, no colour."""
    return {
        "img": {"class_type": "LoadImage", "inputs": {"image": image}},
        "bgm": {"class_type": "LoadBackgroundRemovalModel", "inputs": {"bg_removal_name": MODELS["bg"]}},
        "mask": {"class_type": "RemoveBackground", "inputs": {"bg_removal_model": ["bgm", 0], "image": ["img", 0]}},
        "crop": {"class_type": "ImageCropToMask", "inputs": {"images": ["img", 0], "masks": ["mask", 0], "width": 1024,
                 "height": 1024, "pad_factor": 1.1, "grow_mask": 0, "background": "#ffffff"}},
        "ckpt": {"class_type": "ImageOnlyCheckpointLoader", "inputs": {"ckpt_name": HUNYUAN}},
        "aura": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["ckpt", 0], "shift": 1}},
        "enc": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["ckpt", 1], "image": ["crop", 0], "crop": "center"}},
        "cond": {"class_type": "Hunyuan3Dv2Conditioning", "inputs": {"clip_vision_output": ["enc", 0]}},
        "empty": {"class_type": "EmptyLatentHunyuan3Dv2", "inputs": {"resolution": 4096, "batch_size": 1}},
        "k": {"class_type": "KSampler", "inputs": {"model": ["aura", 0], "seed": seed, "steps": 30, "cfg": 5,
              "sampler_name": "euler", "scheduler": "normal", "positive": ["cond", 0], "negative": ["cond", 1],
              "latent_image": ["empty", 0], "denoise": 1.0}},
        "vae": {"class_type": "VAEDecodeHunyuan3D", "inputs": {"samples": ["k", 0], "vae": ["ckpt", 2], "num_chunks": 8000, "octree_resolution": 256}},
        "mesh": {"class_type": "VoxelToMesh", "inputs": {"voxel": ["vae", 0], "algorithm": "surface net", "threshold": 0.6}},
        "save": {"class_type": "SaveGLB", "inputs": {"mesh": ["mesh", 0], "filename_prefix": prefix}},
    }


def wait(prompt_id: str) -> dict:
    while True:
        h = call(f"/history/{prompt_id}")
        if prompt_id in h:
            entry = h[prompt_id]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                msgs = [m for m in status.get("messages", []) if m[0] == "execution_error"]
                sys.exit(f"ComfyUI failed: {json.dumps(msgs)[:1500]}")
            return entry
        time.sleep(10)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("asset", type=Path, help="folder holding concept.png and asset.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resolution", choices=("32", "64"), default="32")
    ap.add_argument("--tool", choices=("trellis", "hunyuan"), default="trellis",
                    help="hunyuan: Hunyuan3D 2.1, shape only; its licence excludes the EU, UK and South Korea")
    a = ap.parse_args()
    folder = a.asset.resolve()
    concept = folder / "concept.png"
    if not concept.exists():
        sys.exit(f"no concept at {concept}")
    prefix = f"game-model/{folder.name}-s{a.seed}"
    started = time.time()
    image = upload(concept)
    g = hunyuan_graph(image, a.seed, prefix) if a.tool == "hunyuan" else graph(image, a.seed, a.resolution, prefix)
    pid = call("/prompt", json.dumps({"prompt": g}).encode())["prompt_id"]
    print(f"queued {pid}", file=sys.stderr)
    entry = wait(pid)
    files = [f for out in entry["outputs"].values() for v in out.values() if isinstance(v, list)
             for f in v if isinstance(f, dict) and str(f.get("filename", "")).endswith(".glb")]
    if not files:
        sys.exit(f"no .glb in outputs: {json.dumps(entry['outputs'])[:800]}")
    f = files[0]
    q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
    with urllib.request.urlopen(f"{COMFY}/view?{q}", timeout=120) as r:
        (folder / "raw.glb").write_bytes(r.read())
    manifest_path = folder / "asset.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"id": folder.name}
    seconds = round(time.time() - started)
    if a.tool == "hunyuan":
        manifest["model"] = {"tool": "Hunyuan3D 2.1 via ComfyUI (template 3d_hunyuan3d-v2.1), shape only",
                             "weights": {"ckpt": HUNYUAN, "bg": MODELS["bg"]}, "seed": a.seed, "seconds": seconds,
                             "made": time.strftime("%Y-%m-%d"),
                             "licence": "Tencent Hunyuan 3D 2.1 Community License: excludes the EU, UK and South Korea"}
    else:
        manifest["model"] = {
            "tool": "TRELLIS.2 via ComfyUI (template 3d_pixal3d_trellis2_image_to_model, vertex-colour branch)",
            "weights": MODELS, "seed": a.seed, "structure_resolution": a.resolution,
            "seconds": seconds, "made": time.strftime("%Y-%m-%d"),
            "weight_sha256": weight_hashes(),
            "licence": "TRELLIS.2 MIT; BiRefNet MIT; DINOv3 under the DINOv3 License",
        }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{folder / 'raw.glb'} in {manifest['model']['seconds']} s")


if __name__ == "__main__":
    main()
