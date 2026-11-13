#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Record a weapon firing in Godot, with sound, as <asset dir>/fire.mp4 for review.

    game-fire-clip.py <asset dir> [--seconds S]

Reads model.glb, fire.json and sfx/*.wav from the asset folder. fire.json is a
timeline: events at times, each with any of sound, rotate (a cut-out part),
emit (particles from a node for a while), burst (one-shot particle presets),
light, recoil, bolt, move (fly by an offset, spinning), hide; plus "presets" for the particles and "shots" and
"interval_s" to repeat. Example: game-fire-clip.py --example.

Builds a throwaway Godot project in ~/.cache/game-fire-clip/<asset>, records
with --write-movie (needs a logged-in macOS session, not --headless), then
encodes with ffmpeg. The camera frames the model from the side by itself.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GODOT = os.environ.get("GODOT", "godot")
CACHE = Path.home() / ".cache" / "game-fire-clip"

EXAMPLE = {
    "shots": 1,
    "interval_s": 0.5,
    "events": [
        {"at": 0.0, "rotate": {"node": "Hammer", "x_deg": -55, "s": 0.09}, "sound": "hammer.wav"},
        {"at": 0.09, "sound": "fuse.wav",
         "emit": {"preset": "sparks", "node": "Hammer", "offset": [0, 0, -0.04], "for_s": 1.4},
         "light": {"node": "Hammer", "colour": "#ffb347", "energy": 0.6, "s": 1.4}},
        {"at": 1.49, "sound": "bang.wav", "burst": {"presets": ["flash", "smoke"], "node": "Muzzle"},
         "light": {"node": "Muzzle", "colour": "#ffbf66", "energy": 6, "s": 0.08},
         "recoil": {"deg": 9, "back": 0.12}},
    ],
    "presets": {
        "sparks": {"amount": 18, "lifetime": 0.35, "size": 0.006, "emissive": True, "explosiveness": 0.0,
                   "dir": [0, 1, 0], "spread": 60, "speed": [0.3, 0.9], "gravity": -2.0, "colour": "#ffb347"},
        "flash": {"amount": 10, "lifetime": 0.12, "size": 0.03, "emissive": True, "dir": [0, 0, -1],
                  "spread": 25, "speed": [1.5, 3.0], "gravity": 0.0, "colour": "#ffd27a"},
        "smoke": {"amount": 40, "lifetime": 3.0, "size": 0.07, "grow": 4.0, "dir": [0, 0.15, -1], "spread": 35,
                  "speed": [0.4, 1.6], "gravity": 0.12, "damping": 1.2, "colour": "#2a2826"},
    },
}

PROJECT = """config_version=5

[application]
config/name="game-fire-clip"
run/main_scene="res://main.tscn"

[display]
window/size/viewport_width=960
window/size/viewport_height=540

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""

SCENE = """[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="Main" type="Node3D"]
script = ExtResource("1")
"""

MAIN_GD = r'''extends Node3D
## Plays fire.json against model.glb once per shot, then quits.

var fire: Dictionary
var gun: Node3D
var lights: Array[OmniLight3D] = []


func _ready() -> void:
	fire = JSON.parse_string(FileAccess.get_file_as_string("res://fire.json"))
	_stage()
	await get_tree().create_timer(0.6).timeout
	for shot in int(fire.get("shots", 1)):
		_play()
		await get_tree().create_timer(float(fire.get("interval_s", 0.5))).timeout
	await get_tree().create_timer(float(fire.get("tail_s", 2.5))).timeout
	get_tree().quit()


func _stage() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.45, 0.5, 0.55)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.6, 0.65)
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 60, 0)
	sun.light_energy = 1.6
	add_child(sun)
	gun = (load("res://model.glb") as PackedScene).instantiate()
	add_child(gun)
	var box := AABB()
	var first := true
	for m in gun.find_children("*", "MeshInstance3D", true, false):
		var mat := StandardMaterial3D.new()
		mat.vertex_color_use_as_albedo = true
		mat.vertex_color_is_srgb = true
		(m as MeshInstance3D).material_override = mat
		var b: AABB = (m as MeshInstance3D).global_transform * (m as MeshInstance3D).get_aabb()
		box = b if first else box.merge(b)
		first = false
	var cam := Camera3D.new()
	cam.fov = 50
	add_child(cam)
	var span: float = max(box.size.z, box.size.y * 1.6)
	var at := box.get_center() + Vector3(0, 0, -span * 0.2)
	cam.position = at + Vector3(span * 1.25, span * 0.2, 0)
	cam.look_at(at)
	for i in 3:
		var l := OmniLight3D.new()
		l.visible = false
		l.omni_range = span * 2.0
		add_child(l)
		lights.append(l)


func _node(name: String) -> Node3D:
	var n := gun.find_child(name, true, false) as Node3D
	assert(n != null, "no node named %s in model.glb" % name)
	return n


func _at(spec: Dictionary) -> Vector3:
	var o: Array = spec.get("offset", [0, 0, 0])
	return _node(spec["node"]).global_position + Vector3(o[0], o[1], o[2])


func _play() -> void:
	for e in fire["events"]:
		get_tree().create_timer(float(e["at"])).timeout.connect(_event.bind(e))


func _event(e: Dictionary) -> void:
	if e.has("sound"):
		var p := AudioStreamPlayer.new()
		p.stream = load("res://sfx/" + e["sound"])
		p.volume_db = float(e.get("volume_db", 0.0))
		add_child(p)
		p.play()
		p.finished.connect(p.queue_free)
	if e.has("rotate"):
		var r: Dictionary = e["rotate"]
		create_tween().tween_property(_node(r["node"]), "rotation_degrees:x", float(r["x_deg"]), float(r["s"])) \
			.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_IN)
	if e.has("light"):
		var spec: Dictionary = e["light"]
		var l: OmniLight3D = lights.pop_front()
		lights.append(l)
		l.position = _at(spec)
		l.light_color = Color.from_string(spec["colour"], Color.WHITE)
		l.light_energy = float(spec["energy"])
		l.visible = true
		var t := create_tween()
		t.tween_property(l, "light_energy", 0.0, float(spec["s"]))
		t.tween_callback(func(): l.visible = false)
	if e.has("emit"):
		var spec: Dictionary = e["emit"]
		var p := _particles(fire["presets"][spec["preset"]], _at(spec), false)
		get_tree().create_timer(float(spec["for_s"])).timeout.connect(func():
			p.emitting = false
			get_tree().create_timer(2.0).timeout.connect(p.queue_free))
	if e.has("burst"):
		var spec: Dictionary = e["burst"]
		for name in spec["presets"]:
			_particles(fire["presets"][name], _at(spec), true)
	if e.has("recoil"):
		var r: Dictionary = e["recoil"]
		var k := create_tween()
		k.tween_property(gun, "rotation_degrees:x", float(r["deg"]), 0.05)
		k.parallel().tween_property(gun, "position:z", float(r.get("back", 0.0)), 0.05)
		k.tween_property(gun, "rotation_degrees:x", 0.0, 0.5).set_trans(Tween.TRANS_SPRING)
		k.parallel().tween_property(gun, "position:z", 0.0, 0.5)
	if e.has("move"):
		var m: Dictionary = e["move"]
		var by: Array = m["by"]
		var mv := create_tween().set_parallel()
		mv.tween_property(gun, "position", gun.position + Vector3(by[0], by[1], by[2]), float(m["s"])).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		mv.tween_property(gun, "rotation_degrees:x", gun.rotation_degrees.x + float(m.get("spin_deg", 0.0)), float(m["s"]))
	if e.get("hide", false):
		gun.visible = false
	if e.has("bolt"):
		var b: Dictionary = e["bolt"]
		var start := _at({"node": b.get("node", "Muzzle")})
		var bolt := MeshInstance3D.new()
		var mesh := BoxMesh.new()
		var w: float = b.get("width", 0.025)
		mesh.size = Vector3(w, w, float(b.get("length", 0.25)))
		mesh.material = _material(Color.from_string(b["colour"], Color.WHITE), true)
		bolt.mesh = mesh
		bolt.position = start
		add_child(bolt)
		var t := create_tween()
		t.tween_property(bolt, "position:z", start.z - float(b["range"]), float(b["s"]))
		t.tween_callback(bolt.queue_free)


func _material(colour: Color, emissive: bool) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.albedo_color = colour
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	if emissive:
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return mat


func _particles(preset: Dictionary, at: Vector3, one_shot: bool) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = float(preset["size"])
	mesh.height = float(preset["size"]) * 2
	mesh.radial_segments = 6
	mesh.rings = 3
	mesh.material = _material(Color.WHITE, preset.get("emissive", false))
	p.mesh = mesh
	p.position = at
	p.amount = int(preset["amount"])
	p.lifetime = float(preset["lifetime"])
	p.one_shot = one_shot
	p.explosiveness = float(preset.get("explosiveness", 0.9))
	var d: Array = preset["dir"]
	p.direction = Vector3(d[0], d[1], d[2])
	p.spread = float(preset["spread"])
	p.initial_velocity_min = float(preset["speed"][0])
	p.initial_velocity_max = float(preset["speed"][1])
	p.gravity = Vector3(0, float(preset["gravity"]), 0)
	p.damping_min = float(preset.get("damping", 0.0))
	p.damping_max = p.damping_min
	var grow := Curve.new()
	grow.max_value = max(1.0, float(preset.get("grow", 1.0)))
	grow.add_point(Vector2(0, 0.4))
	grow.add_point(Vector2(1, float(preset.get("grow", 1.0))))
	p.scale_amount_curve = grow
	var ramp := Gradient.new()
	var c := Color.from_string(preset["colour"], Color.WHITE)
	ramp.set_color(0, c)
	c.a = 0.0
	ramp.set_color(1, c)
	p.color_ramp = ramp
	add_child(p)
	p.emitting = true
	if one_shot:
		get_tree().create_timer(p.lifetime + 0.5).timeout.connect(p.queue_free)
	return p
'''


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"{cmd[0]} failed ({r.returncode}):\n{r.stderr[-2000:]}")
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("asset", type=Path, nargs="?", help="folder holding model.glb, fire.json and sfx/")
    ap.add_argument("--example", action="store_true", help="print an example fire.json (a musket) and exit")
    a = ap.parse_args()
    if a.example:
        print(json.dumps(EXAMPLE, indent=2))
        return
    if not a.asset:
        ap.error("give an asset folder, or --example")
    folder = a.asset.resolve()
    for need in ("model.glb", "fire.json"):
        if not (folder / need).exists():
            sys.exit(f"missing {folder / need}")
    proj = CACHE / folder.name
    (proj / "sfx").mkdir(parents=True, exist_ok=True)
    (proj / "project.godot").write_text(PROJECT)
    (proj / "main.tscn").write_text(SCENE)
    (proj / "main.gd").write_text(MAIN_GD)
    shutil.copy(folder / "model.glb", proj / "model.glb")
    shutil.copy(folder / "fire.json", proj / "fire.json")
    for wav in (folder / "sfx").glob("*.wav"):
        shutil.copy(wav, proj / "sfx" / wav.name)
    run([GODOT, "--headless", "--path", str(proj), "--import"], timeout=300)
    avi = proj / "fire.avi"
    r = run([GODOT, "--path", str(proj), "--write-movie", str(avi), "--fixed-fps", "30", "--resolution", "960x540"], timeout=300)
    errors = [l for l in r.stderr.splitlines() + r.stdout.splitlines() if "SCRIPT ERROR" in l or "Assertion failed" in l]
    if errors:
        sys.exit("Godot script errors:\n" + "\n".join(errors[:10]))
    out = folder / "fire.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(avi), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", str(out)], timeout=300)
    print(out)


if __name__ == "__main__":
    main()
