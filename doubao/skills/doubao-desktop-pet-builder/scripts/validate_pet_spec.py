#!/usr/bin/env python3
"""Validate the desktop-pet v5 contract without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


INPUT_TYPES = {"single-image", "action-pack", "text", "existing-project"}
STYLES = {"preserve", "balanced-cartoon", "key-elements", "custom"}
ARCHETYPES = {"cat", "dog", "rabbit", "bird", "reptile", "fish", "fantasy", "person", "robot", "object", "custom"}
INTERRUPTS = {"resume", "restart", "discard", "block"}
DIRECTIONS = {"neutral", "left", "right"}
APP_ID = re.compile(r"^[A-Za-z][A-Za-z0-9]*(\.[A-Za-z0-9-]+)+$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRIGGER = re.compile(r"^[a-z][a-z-]*:[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
BUILTIN_TRIGGERS = {
    "app:start", "ambient:idle", "ambient:blink", "ambient:random",
    "pointer:tap", "window:drag", "window:edge-snap", "reminder:due",
    "typing:activity", "file:drop", "file:drop-success", "file:drop-fail",
    "movement:left", "movement:right",
}
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "references" / "pet-spec.schema.json"


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def schema_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return type(value) is bool
    if expected == "integer":
        return type(value) is int
    if expected == "number":
        return (type(value) is int or type(value) is float) and value == value
    return True


def resolve_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema ref: {ref}")
    current: Any = root_schema
    for part in ref[2:].split("/"):
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"schema ref does not point to an object: {ref}")
    return current


def validate_against_schema(value: Any, schema: dict[str, Any], root_schema: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    root_schema = schema if root_schema is None else root_schema
    if "$ref" in schema:
        return validate_against_schema(value, resolve_ref(root_schema, schema["$ref"]), root_schema, path)

    errors: list[str] = []
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not schema_type_matches(value, expected_type):
        return [f"{path}: must match schema type {expected_type}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']!r}")

    if isinstance(value, str):
        if isinstance(schema.get("minLength"), int) and len(value) < schema["minLength"]:
            errors.append(f"{path}: must be at least {schema['minLength']} characters")
        if isinstance(schema.get("maxLength"), int) and len(value) > schema["maxLength"]:
            errors.append(f"{path}: must be at most {schema['maxLength']} characters")
        if isinstance(schema.get("pattern"), str) and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: must match pattern {schema['pattern']}")

    if type(value) in {int, float}:
        if isinstance(schema.get("minimum"), (int, float)) and value < schema["minimum"]:
            errors.append(f"{path}: must be >= {schema['minimum']}")
        if isinstance(schema.get("maximum"), (int, float)) and value > schema["maximum"]:
            errors.append(f"{path}: must be <= {schema['maximum']}")

    if isinstance(value, list):
        if isinstance(schema.get("minItems"), int) and len(value) < schema["minItems"]:
            errors.append(f"{path}: must contain at least {schema['minItems']} items")
        if isinstance(schema.get("maxItems"), int) and len(value) > schema["maxItems"]:
            errors.append(f"{path}: must contain at most {schema['maxItems']} items")
        if schema.get("uniqueItems") is True:
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_against_schema(item, item_schema, root_schema, f"{path}[{index}]"))

    if isinstance(value, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    errors.append(f"{path}.{key}: is required by schema")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            if schema.get("additionalProperties") is False:
                unknown = sorted(set(value) - set(properties))
                if unknown:
                    errors.append(f"{path}: unknown schema keys {unknown}")
            for key, item_schema in properties.items():
                if key in value and isinstance(item_schema, dict):
                    errors.extend(validate_against_schema(value[key], item_schema, root_schema, f"{path}.{key}"))

    return errors


def looks_like_utf8_gbk_mojibake(value: str) -> bool:
    """Detect the common case where UTF-8 Chinese was decoded as GBK then saved."""
    if "\ufffd" in value or any(marker in value for marker in ("锛", "鈥", "灏忛噾", "妗屽疇", "鍠傚皬", "鎽告懜")):
        return True
    try:
        repaired = value.encode("gbk").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    return repaired != value and any("\u4e00" <= char <= "\u9fff" for char in repaired)


def walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)


def is_safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return False
    return ".." not in PurePosixPath(normalized).parts


def validate(spec: Any) -> list[str]:
    errors: list[str] = validate_against_schema(spec, load_schema())

    def need(condition: bool, path: str, message: str) -> None:
        if not condition:
            errors.append(f"{path}: {message}")

    if not isinstance(spec, dict):
        return ["$: must be an object"]

    top = {"schemaVersion", "app", "targets", "character", "assetPipeline", "experience", "motion", "features", "states", "storage", "build"}
    need(set(spec) == top, "$", f"must contain exactly {sorted(top)}")
    need(spec.get("schemaVersion") == 5, "$.schemaVersion", "must equal 5")
    suspicious_strings = [value for value in walk_strings(spec) if looks_like_utf8_gbk_mojibake(value)]
    need(not suspicious_strings, "$", "contains probable UTF-8/GBK mojibake; restore the UTF-8 source instead of saving the damaged text")

    app = spec.get("app")
    need(isinstance(app, dict), "$.app", "must be an object")
    if isinstance(app, dict):
        need(set(app) == {"name", "appId", "version", "language"}, "$.app", "has missing or unknown keys")
        need(isinstance(app.get("name"), str) and 1 <= len(app["name"]) <= 64, "$.app.name", "must be 1-64 characters")
        need(isinstance(app.get("appId"), str) and bool(APP_ID.fullmatch(app["appId"])), "$.app.appId", "must be a reverse-domain identifier")
        need(isinstance(app.get("version"), str) and bool(SEMVER.fullmatch(app["version"])), "$.app.version", "must be semver")
        need(isinstance(app.get("language"), str) and 2 <= len(app["language"]) <= 16, "$.app.language", "must be 2-16 characters")

    targets = spec.get("targets")
    need(isinstance(targets, dict) and set(targets) == {"windows", "macos"}, "$.targets", "must contain windows and macos")
    if isinstance(targets, dict):
        for platform in ("windows", "macos"):
            target = targets.get(platform)
            need(isinstance(target, dict) and set(target) == {"enabled", "arch"}, f"$.targets.{platform}", "must contain enabled and arch")
            if isinstance(target, dict):
                need(type(target.get("enabled")) is bool, f"$.targets.{platform}.enabled", "must be boolean")
                allowed = {"x64"} if platform == "windows" else {"current", "arm64", "x64"}
                need(target.get("arch") in allowed, f"$.targets.{platform}.arch", f"must be one of {sorted(allowed)}")

    character = spec.get("character")
    character_keys = {"inputType", "coreAsset", "displayName", "archetype", "personality", "preserveTraits", "style", "mirrorSafe"}
    need(isinstance(character, dict) and set(character) == character_keys, "$.character", f"must contain exactly {sorted(character_keys)}")
    if isinstance(character, dict):
        need(character.get("inputType") in INPUT_TYPES, "$.character.inputType", "invalid input type")
        need(is_safe_relative(character.get("coreAsset")), "$.character.coreAsset", "must be a safe relative path")
        need(isinstance(character.get("displayName"), str) and 1 <= len(character["displayName"]) <= 32, "$.character.displayName", "must be 1-32 characters")
        need(character.get("archetype") in ARCHETYPES, "$.character.archetype", "invalid archetype")
        personality = character.get("personality")
        need(isinstance(personality, list) and 1 <= len(personality) <= 8 and all(isinstance(x, str) and 1 <= len(x) <= 24 for x in personality), "$.character.personality", "must contain 1-8 short strings")
        traits = character.get("preserveTraits")
        need(isinstance(traits, list) and 1 <= len(traits) <= 20 and all(isinstance(x, str) and 1 <= len(x) <= 80 for x in traits), "$.character.preserveTraits", "must contain 1-20 strings")
        need(character.get("style") in STYLES, "$.character.style", "invalid style")
        need(type(character.get("mirrorSafe")) is bool, "$.character.mirrorSafe", "must be boolean")

    asset_pipeline = spec.get("assetPipeline")
    asset_pipeline_keys = {
        "backgroundMode",
        "segmentationBackend",
        "subjectKind",
        "generationBackground",
        "backgroundTolerance",
        "edgeFeather",
        "safeMargin",
        "targetOccupancy",
    }
    need(isinstance(asset_pipeline, dict) and set(asset_pipeline) == asset_pipeline_keys, "$.assetPipeline", f"must contain exactly {sorted(asset_pipeline_keys)}")
    if isinstance(asset_pipeline, dict):
        need(asset_pipeline.get("backgroundMode") == "semantic-cutout", "$.assetPipeline.backgroundMode", "must equal semantic-cutout")
        need(asset_pipeline.get("segmentationBackend") in {"auto", "apple-vision", "rembg"}, "$.assetPipeline.segmentationBackend", "must be auto, apple-vision or rembg")
        need(asset_pipeline.get("subjectKind") in {"auto", "illustration", "photo"}, "$.assetPipeline.subjectKind", "must be auto, illustration or photo")
        need(asset_pipeline.get("generationBackground") in {"transparent-grid", "solid-chroma"}, "$.assetPipeline.generationBackground", "must be transparent-grid or solid-chroma")
        need(type(asset_pipeline.get("backgroundTolerance")) is int and 12 <= asset_pipeline["backgroundTolerance"] <= 48, "$.assetPipeline.backgroundTolerance", "must be 12-48")
        need(type(asset_pipeline.get("edgeFeather")) is int and 4 <= asset_pipeline["edgeFeather"] <= 24, "$.assetPipeline.edgeFeather", "must be 4-24")
        need(type(asset_pipeline.get("safeMargin")) is int and 16 <= asset_pipeline["safeMargin"] <= 64, "$.assetPipeline.safeMargin", "must be 16-64")
        need(isinstance(asset_pipeline.get("targetOccupancy"), (int, float)) and 0.65 <= asset_pipeline["targetOccupancy"] <= 0.82, "$.assetPipeline.targetOccupancy", "must be 0.65-0.82")

    experience = spec.get("experience")
    need(isinstance(experience, dict) and set(experience) == {"theme", "interactions", "petSizing"}, "$.experience", "must contain theme, interactions and petSizing")
    interactions: list[Any] = []
    if isinstance(experience, dict):
        theme = experience.get("theme")
        theme_keys = {"primary", "accent", "background", "surface", "text", "muted", "cornerRadius"}
        need(isinstance(theme, dict) and set(theme) == theme_keys, "$.experience.theme", f"must contain exactly {sorted(theme_keys)}")
        if isinstance(theme, dict):
            for key in theme_keys - {"cornerRadius"}:
                need(isinstance(theme.get(key), str) and bool(HEX.fullmatch(theme[key])), f"$.experience.theme.{key}", "must be #RRGGBB")
            need(type(theme.get("cornerRadius")) is int and 12 <= theme["cornerRadius"] <= 32, "$.experience.theme.cornerRadius", "must be 12-32")
        interactions = experience.get("interactions") if isinstance(experience.get("interactions"), list) else []
        need(isinstance(experience.get("interactions"), list) and len(interactions) <= 6, "$.experience.interactions", "must contain at most 6 interactions")
        pet_sizing = experience.get("petSizing")
        need(isinstance(pet_sizing, dict) and set(pet_sizing) == {"baseWindowPx", "defaultScale"}, "$.experience.petSizing", "must contain baseWindowPx and defaultScale")
        if isinstance(pet_sizing, dict):
            need(type(pet_sizing.get("baseWindowPx")) is int and 180 <= pet_sizing["baseWindowPx"] <= 260, "$.experience.petSizing.baseWindowPx", "must be 180-260")
            need(pet_sizing.get("defaultScale") in {0.65, 0.8, 1, 1.2}, "$.experience.petSizing.defaultScale", "must be one of 0.65, 0.8, 1, 1.2")

    interaction_ids: set[str] = set()
    interaction_state_ids: set[str] = set()
    for index, interaction in enumerate(interactions):
        path = f"$.experience.interactions[{index}]"
        expected = {"id", "emoji", "label", "stateId", "durationMs", "affectionGain", "feedback"}
        need(isinstance(interaction, dict) and set(interaction) == expected, path, f"must contain exactly {sorted(expected)}")
        if not isinstance(interaction, dict):
            continue
        interaction_id = interaction.get("id")
        state_id = interaction.get("stateId")
        need(isinstance(interaction_id, str) and bool(SLUG.fullmatch(interaction_id)), f"{path}.id", "invalid id")
        if isinstance(interaction_id, str):
            need(interaction_id not in interaction_ids, f"{path}.id", "duplicate interaction id")
            interaction_ids.add(interaction_id)
        need(isinstance(interaction.get("label"), str) and 1 <= len(interaction["label"]) <= 24, f"{path}.label", "must be 1-24 characters")
        need(isinstance(interaction.get("emoji"), str) and 1 <= len(interaction["emoji"]) <= 8, f"{path}.emoji", "must be a short menu icon")
        need(isinstance(state_id, str) and bool(SLUG.fullmatch(state_id)), f"{path}.stateId", "invalid state id")
        if isinstance(state_id, str):
            interaction_state_ids.add(state_id)
        need(type(interaction.get("durationMs")) is int and 300 <= interaction["durationMs"] <= 10000, f"{path}.durationMs", "must be 300-10000")
        need(type(interaction.get("affectionGain")) is int and 0 <= interaction["affectionGain"] <= 20, f"{path}.affectionGain", "must be 0-20")
        feedback = interaction.get("feedback")
        need(isinstance(feedback, list) and 2 <= len(feedback) <= 6 and all(isinstance(x, str) and 1 <= len(x) <= 40 for x in feedback), f"{path}.feedback", "must contain 2-6 short strings")

    motion = spec.get("motion")
    need(isinstance(motion, dict) and set(motion) == {"breathing", "squashStretch", "idleIntervalMs"}, "$.motion", "invalid motion object")
    if isinstance(motion, dict):
        breathing = motion.get("breathing")
        need(isinstance(breathing, dict) and set(breathing) == {"enabled", "periodMs", "scaleX", "scaleY"}, "$.motion.breathing", "invalid breathing object")
        if isinstance(breathing, dict):
            need(type(breathing.get("enabled")) is bool, "$.motion.breathing.enabled", "must be boolean")
            need(type(breathing.get("periodMs")) is int and 1800 <= breathing["periodMs"] <= 8000, "$.motion.breathing.periodMs", "must be 1800-8000")
            for key, maximum in (("scaleX", 0.04), ("scaleY", 0.05)):
                need(isinstance(breathing.get(key), (int, float)) and 0 <= breathing[key] <= maximum, f"$.motion.breathing.{key}", f"must be 0-{maximum}")
        squash = motion.get("squashStretch")
        need(isinstance(squash, dict) and set(squash) == {"enabled", "durationMs", "intensity"}, "$.motion.squashStretch", "invalid squashStretch object")
        if isinstance(squash, dict):
            need(type(squash.get("enabled")) is bool, "$.motion.squashStretch.enabled", "must be boolean")
            need(type(squash.get("durationMs")) is int and 160 <= squash["durationMs"] <= 600, "$.motion.squashStretch.durationMs", "must be 160-600")
            need(isinstance(squash.get("intensity"), (int, float)) and 0 <= squash["intensity"] <= 0.15, "$.motion.squashStretch.intensity", "must be 0-0.15")
        idle = motion.get("idleIntervalMs")
        need(isinstance(idle, dict) and set(idle) == {"min", "max"}, "$.motion.idleIntervalMs", "must contain min and max")
        if isinstance(idle, dict):
            need(type(idle.get("min")) is int and 3000 <= idle["min"] <= 60000, "$.motion.idleIntervalMs.min", "must be 3000-60000")
            need(type(idle.get("max")) is int and 3000 <= idle["max"] <= 120000, "$.motion.idleIntervalMs.max", "must be 3000-120000")
            if isinstance(idle.get("min"), int) and isinstance(idle.get("max"), int):
                need(idle["min"] <= idle["max"], "$.motion.idleIntervalMs", "min must not exceed max")

    feature_keys = {"transparentWindow", "drag", "tray", "edgeSnap", "reminders", "interactions", "relationship", "filePocket", "dashboard", "typingReaction", "autonomousMovement"}
    features = spec.get("features")
    need(isinstance(features, dict) and set(features) == feature_keys, "$.features", f"must contain exactly {sorted(feature_keys)}")
    if isinstance(features, dict):
        for key in feature_keys:
            need(type(features.get(key)) is bool, f"$.features.{key}", "must be boolean")
        need(features.get("transparentWindow") is True, "$.features.transparentWindow", "must be true")
        need(not features.get("relationship") or features.get("interactions"), "$.features.relationship", "requires interactions")
        need(not features.get("interactions") or 2 <= len(interactions) <= 6, "$.experience.interactions", "enabled interactions require 2-6 entries")
        need(features.get("interactions") or len(interactions) == 0, "$.experience.interactions", "must be empty when interactions are disabled")

    states = spec.get("states")
    need(isinstance(states, list) and 4 <= len(states) <= 40, "$.states", "must contain 4-40 states")
    state_ids: set[str] = set()
    trigger_to_state: dict[str, str] = {}
    state_frames: dict[str, list[str]] = {}
    frame_owners: dict[str, str] = {}
    if isinstance(states, list):
        for index, state in enumerate(states):
            path = f"$.states[{index}]"
            expected = {"id", "triggers", "frames", "frameDurationMs", "loop", "priority", "interrupt", "cooldownMs", "direction", "anchor", "mirrorSafe"}
            need(isinstance(state, dict) and set(state) == expected, path, f"must contain exactly {sorted(expected)}")
            if not isinstance(state, dict):
                continue
            state_id = state.get("id")
            need(isinstance(state_id, str) and bool(SLUG.fullmatch(state_id)), f"{path}.id", "invalid state id")
            if isinstance(state_id, str):
                need(state_id not in state_ids, f"{path}.id", "duplicate state id")
                state_ids.add(state_id)
            frames = state.get("frames")
            need(isinstance(frames, list) and 1 <= len(frames) <= 24 and all(is_safe_relative(x) for x in frames), f"{path}.frames", "must contain 1-24 safe paths")
            if isinstance(frames, list) and isinstance(state_id, str):
                need(len(frames) == len(set(frames)), f"{path}.frames", "must not repeat a frame filename")
                state_frames[state_id] = frames
                for frame in frames:
                    if not isinstance(frame, str):
                        continue
                    need(frame not in frame_owners, f"{path}.frames", f"frame already belongs to state {frame_owners.get(frame)}")
                    frame_owners.setdefault(frame, state_id)
            triggers = state.get("triggers")
            need(isinstance(triggers, list) and 1 <= len(triggers) <= 12 and len(triggers) == len(set(triggers)) and all(isinstance(x, str) and bool(TRIGGER.fullmatch(x)) for x in triggers), f"{path}.triggers", "must contain 1-12 unique valid triggers")
            if isinstance(triggers, list):
                for trigger in triggers:
                    if not isinstance(trigger, str):
                        continue
                    valid = trigger in BUILTIN_TRIGGERS or (trigger.startswith("interaction:") and trigger.removeprefix("interaction:") in interaction_ids)
                    need(valid, f"{path}.triggers", f"unknown trigger: {trigger}")
                    need(trigger not in trigger_to_state, f"{path}.triggers", f"trigger already mapped by {trigger_to_state.get(trigger)}")
                    if trigger not in trigger_to_state and isinstance(state_id, str):
                        trigger_to_state[trigger] = state_id
            need(type(state.get("frameDurationMs")) is int and 40 <= state["frameDurationMs"] <= 10000, f"{path}.frameDurationMs", "must be 40-10000")
            need(type(state.get("loop")) is bool, f"{path}.loop", "must be boolean")
            need(type(state.get("priority")) is int and 0 <= state["priority"] <= 1000, f"{path}.priority", "must be 0-1000")
            need(state.get("interrupt") in INTERRUPTS, f"{path}.interrupt", "invalid strategy")
            need(type(state.get("cooldownMs")) is int and 0 <= state["cooldownMs"] <= 3600000, f"{path}.cooldownMs", "must be 0-3600000")
            need(state.get("direction") in DIRECTIONS, f"{path}.direction", "invalid direction")
            anchor = state.get("anchor")
            need(isinstance(anchor, dict) and set(anchor) == {"x", "y"}, f"{path}.anchor", "must contain x and y")
            if isinstance(anchor, dict):
                need(isinstance(anchor.get("x"), (int, float)) and 0 <= anchor["x"] <= 1, f"{path}.anchor.x", "must be 0-1")
                need(isinstance(anchor.get("y"), (int, float)) and 0 <= anchor["y"] <= 1, f"{path}.anchor.y", "must be 0-1")
            need(type(state.get("mirrorSafe")) is bool, f"{path}.mirrorSafe", "must be boolean")

    if isinstance(character, dict):
        core_asset = character.get("coreAsset")
        need(core_asset not in frame_owners, "$.character.coreAsset", "must be an independent identity master, not a runtime animation frame")

    for required in ("app:start", "ambient:idle", "ambient:blink", "pointer:tap"):
        need(required in trigger_to_state, "$.states", f"missing required trigger: {required}")
    need("idle" in state_ids, "$.states", "state machine requires an idle state")
    conditional = {
        "reminders": ["reminder:due"],
        "edgeSnap": ["window:edge-snap"],
        "typingReaction": ["typing:activity"],
        "filePocket": ["file:drop", "file:drop-success", "file:drop-fail"],
        "autonomousMovement": ["movement:left", "movement:right"],
    }
    if isinstance(features, dict):
        for feature, required_triggers in conditional.items():
            if features.get(feature):
                for trigger in required_triggers:
                    need(trigger in trigger_to_state, "$.states", f"{feature} requires trigger {trigger}")
            else:
                for trigger in required_triggers:
                    need(trigger not in trigger_to_state, "$.states", f"{trigger} must be absent while {feature} is disabled")

    for interaction_id in interaction_ids:
        need(f"interaction:{interaction_id}" in trigger_to_state, "$.states", f"missing trigger for interaction {interaction_id}")
    for state_id in interaction_state_ids:
        need(state_id in state_ids, "$.experience.interactions", f"unknown interaction state: {state_id}")
        need(5 <= len(state_frames.get(state_id, [])) <= 6, "$.states", f"interaction state {state_id} must have 5-6 frames")
    blink_state = trigger_to_state.get("ambient:blink")
    if blink_state:
        need(len(state_frames.get(blink_state, [])) == 5, "$.states", "blink state must have exactly 5 frames")
    need(4 <= len(state_frames.get("idle", [])) <= 6, "$.states", "idle state must have 4-6 frames")
    for trigger in ("pointer:tap", "reminder:due", "window:edge-snap", "ambient:random"):
        state_id = trigger_to_state.get(trigger)
        if state_id:
            need(5 <= len(state_frames.get(state_id, [])) <= 6, "$.states", f"{trigger} state {state_id} must have 5-6 frames")
    for trigger in ("movement:left", "movement:right"):
        state_id = trigger_to_state.get(trigger)
        if state_id:
            need(6 <= len(state_frames.get(state_id, [])) <= 8, "$.states", f"{trigger} state {state_id} must have 6-8 frames")
    for interaction in interactions:
        if not isinstance(interaction, dict):
            continue
        state_id = interaction.get("stateId")
        state = next((item for item in states if isinstance(item, dict) and item.get("id") == state_id), None) if isinstance(states, list) else None
        if isinstance(state, dict) and isinstance(interaction.get("durationMs"), int) and isinstance(state.get("frameDurationMs"), int):
            minimum_duration = len(state.get("frames", [])) * state["frameDurationMs"]
            need(interaction["durationMs"] >= minimum_duration, "$.experience.interactions", f"interaction {interaction.get('id')} duration must cover at least one full animation cycle ({minimum_duration}ms)")

    need(spec.get("storage") == {"userData": "app-user-data", "filePocket": "documents-app-name"}, "$.storage", "must use cross-platform path policies")

    build = spec.get("build")
    need(isinstance(build, dict) and set(build) == {"windows", "macos", "timeoutMinutes", "unsigned"}, "$.build", "invalid build object")
    if isinstance(build, dict):
        windows = build.get("windows")
        need(windows == {"arch": "x64", "installer": "squirrel", "portable": "zip"}, "$.build.windows", "must use x64/squirrel/zip")
        macos = build.get("macos")
        need(isinstance(macos, dict) and set(macos) == {"arch", "diskImage", "portable"}, "$.build.macos", "invalid macOS build")
        if isinstance(macos, dict):
            need(macos.get("arch") in {"current", "arm64", "x64"}, "$.build.macos.arch", "invalid architecture")
            need(macos.get("diskImage") == "dmg" and macos.get("portable") == "zip", "$.build.macos", "must use dmg and zip")
        need(type(build.get("timeoutMinutes")) is int and 5 <= build["timeoutMinutes"] <= 60, "$.build.timeoutMinutes", "must be 5-60")
        need(build.get("unsigned") is True, "$.build.unsigned", "must explicitly be true")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: cannot read JSON: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        print("INVALID pet-spec.json", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"VALID pet-spec.json v5: {args.spec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
