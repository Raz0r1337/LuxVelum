# Lamp rules ported from Everwood (https://github.com/pkuzic/benilla-everwood_graphics),
# Copyright (c) 2026 Sam, MIT licence: see tools/LICENSE-Everwood-MIT.txt
import math
from typing import Iterable, List, Optional, Sequence, Tuple

from lamp_types import (FLAG_BOUNDS_FALLBACK, FLAG_CLAMPED_TO_MODEL, FLAG_DEAD_AUTHORED_BLOCKS, KIND_BONFIRE,
                        KIND_BRAZIER, KIND_CANDLE, KIND_CHANDELIER, KIND_LAMP, KIND_TORCH, ROUTE_AUTHORED,
                        ROUTE_EMISSIVE, ROUTE_FLAME, ROUTE_NAME, ROUTE_RESTORED, M2Batch, M2Emitter, M2Light,
                        M2Model, ModelLamp, ModelVerdict, Vec3)

POINT_LIGHT = 1
MIN_EMITTED_LIGHT = 0.01
DEFAULT_AUTHORED_REACH = 12.0

RESTORE_MAX_CENTRE_OFFSET = 2.0
RESTORE_MIN_EXTENT_RATIO = 0.5
RESTORE_MAX_EXTENT_RATIO = 2.0
BOX_EXTENT_FLOOR = 0.05

FIRE_TEXTURE_KEYS = ("FLAMELICK", "BONFIRE", "BRAZIER", "CANDLE", "TORCH", "FLAME", "EMBER", "FIRE")
PARTICLE_NO_ALPHA_ADD = 3
PARTICLE_ADD = 4
PARTICLE_BLEND_ADD = 7
ADDITIVE_PARTICLE_BLENDS = frozenset((PARTICLE_NO_ALPHA_ADD, PARTICLE_ADD, PARTICLE_BLEND_ADD))
MIN_FLAME_SIZE = 0.04
RATE_ROOT = 0.25
MIN_SATURATION = 0.15
VISIBLE_KEY_ALPHA = 0.05
BLACK_PEAK = 1e-4

DEFAULT_WARM: Vec3 = (1.0, 0.55, 0.2)
DEFAULT_LAMP: Vec3 = (1.0, 0.72, 0.40)
COLD_COLOUR_FLOOR = 0.40

CANDLE_INTENSITY = 0.6
TORCH_INTENSITY = 1.5
BRAZIER_INTENSITY = 2.0
BONFIRE_INTENSITY = 3.0
FLAME_TIERS = ((0.25, CANDLE_INTENSITY, KIND_CANDLE), (0.70, TORCH_INTENSITY, KIND_TORCH),
               (1.60, BRAZIER_INTENSITY, KIND_BRAZIER))
TOP_FLAME_TIER = (BONFIRE_INTENSITY, KIND_BONFIRE)
REACH_TIERS = ((1.0, 6.0), (1.75, 12.0), (2.5, 16.0))
TOP_REACH = 24.0

LAMP_NAME_KEYS = (("CHANDELIER", KIND_CHANDELIER), ("CANDELABRA", KIND_CANDLE), ("LAMPPOST", KIND_LAMP),
                  ("LAMP POST", KIND_LAMP), ("LIGHTPOST", KIND_LAMP), ("STREETLAMP", KIND_LAMP),
                  ("STREETLIGHT", KIND_LAMP), ("LANTERN", KIND_LAMP), ("SCONCE", KIND_LAMP), ("LAMP", KIND_LAMP),
                  ("CANDLE", KIND_CANDLE), ("BRAZIER", KIND_BRAZIER), ("TORCH", KIND_TORCH))
OPEN_FIRE_KINDS = frozenset((KIND_BRAZIER, KIND_TORCH))
LAMP_DIR_KEYS = ("LAMP", "LANTERN", "CANDLE", "SCONCE", "CHANDELIER", "LIGHTS", "TORCH")
BEAM_KEYS = ("SHAFT", "BEAM", "SKYLIGHT")
GLOW_TEXTURE_KEYS = ("GLOW", "LIGHT", "LAMP", "LANTERN", "FLARE", "FIRE", "FLAME", "CANDLE", "TORCH")
BROKEN_KEYS = ("BROKEN", "BUSTED", "WRECKED", "SMASHED", "DESTROY", "FALLEN", "UNLIT")
OFF_SUFFIX = "OFF"
SERIAL_DIGITS = "0123456789"
SERIAL_SEPARATORS = "_-"
NAME_TINTS = (("BLUE", (0.45, 0.65, 1.0)), ("GREEN", (0.40, 1.0, 0.45)), ("PURPLE", (0.70, 0.40, 1.0)),
              ("ARCANE", (0.70, 0.40, 1.0)), ("RED", (1.0, 0.35, 0.25)))
SHADED_LAMP_KEYS = ("LAMP", "LANTERN", "POST", "SCONCE", "CANDLE", "CHANDELIER")
LAMP_INTENSITIES = {KIND_CHANDELIER: BRAZIER_INTENSITY, KIND_CANDLE: CANDLE_INTENSITY,
                    KIND_BRAZIER: BRAZIER_INTENSITY, KIND_TORCH: TORCH_INTENSITY}
GENERIC_LAMP_INTENSITY = TORCH_INTENSITY

BATCH_ALPHA = 2
BATCH_NO_ALPHA_ADD = 3
BATCH_ADD = 4
BATCH_BLEND_ADD = 7
TRANSPARENT_BATCH_BLENDS = frozenset((BATCH_ALPHA, BATCH_NO_ALPHA_ADD, BATCH_ADD, BATCH_BLEND_ADD))

PATH_SEPARATOR = "\\"
WORLD_ROOTS = ("WORLD\\", "DUNGEONS\\")
SPELL_ROOT = "SPELLS\\"
SPELL_SEGMENT = "\\SPELLS\\"
CARRIED_ITEM_ROOT = "ITEM\\OBJECTCOMPONENTS\\"

FAR_FLAME_MIN_MARGIN = 2.0
FAR_FLAME_BOX_FRACTION = 0.5

NOTE_SPELL_EFFECT = "spell effect"
NOTE_DEAD_BLOCKS = "dead blocks"
NOTE_BOXES_DIFFER = "boxes differ"
NOTE_LIVE_NON_POINT_LIGHT = "live non-point light block"
NOTE_FLAME_CLAMPED = "flame clamped into the model box"
NOTE_BOUNDS_FALLBACK = "top-of-box fallback"


def finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def contains_any(text: str, keys: Sequence[str]) -> bool:
    return any(key in text for key in keys)


def normalized_path(path: str) -> str:
    return path.replace("/", PATH_SEPARATOR).upper()


def basename_stem(path: str) -> str:
    return normalized_path(path).rsplit(PATH_SEPARATOR, 1)[-1].split(".", 1)[0]


def directory(path: str) -> Optional[str]:
    normalized = normalized_path(path)
    end = normalized.rfind(PATH_SEPARATOR)
    return normalized[:end] if end >= 0 else None


def is_spell_path(path: str) -> bool:
    normalized = normalized_path(path)
    return normalized.startswith(SPELL_ROOT) or SPELL_SEGMENT in normalized


def lamp_kind(path: str) -> Optional[int]:
    stem = basename_stem(path)
    for key, kind in LAMP_NAME_KEYS:
        if key in stem:
            return kind
    return None


def is_broken_or_off(path: str) -> bool:
    stem = basename_stem(path)
    unnumbered = stem.rstrip(SERIAL_DIGITS).rstrip(SERIAL_SEPARATORS)
    return contains_any(stem, BROKEN_KEYS) or unnumbered.endswith(OFF_SUFFIX)


def is_light_beam(path: str) -> bool:
    return contains_any(basename_stem(path), BEAM_KEYS)


def in_lamp_dir(path: str) -> bool:
    folder = directory(path)
    return folder is not None and contains_any(folder, LAMP_DIR_KEYS)


def lamp_family_ok(path: str) -> bool:
    normalized = normalized_path(path)
    return (normalized.startswith(WORLD_ROOTS) and SPELL_SEGMENT not in normalized
            and not normalized.startswith(CARRIED_ITEM_ROOT))


def is_lamp_like(path: str) -> bool:
    return not is_spell_path(path) and (lamp_kind(path) is not None or in_lamp_dir(path))


def fire_texture(texture: str) -> bool:
    return bool(texture) and contains_any(basename_stem(texture), FIRE_TEXTURE_KEYS)


def glow_texture(texture: str) -> bool:
    if not texture:
        return False
    stem = basename_stem(texture)
    return not contains_any(stem, BEAM_KEYS) and contains_any(stem, GLOW_TEXTURE_KEYS)


def peak_light_color(light: M2Light) -> float:
    return max(light.diffuse_color)


def is_live_block(light: M2Light) -> bool:
    peak = peak_light_color(light)
    return (light.visible and finite(light.diffuse_color) and math.isfinite(light.diffuse_intensity)
            and peak > 0.0 and light.diffuse_intensity > 0.0 and peak * light.diffuse_intensity >= MIN_EMITTED_LIGHT)


def is_emitting_point_light(light: M2Light) -> bool:
    return light.light_type == POINT_LIGHT and is_live_block(light) and finite(light.position)


def emitting_point_lights(model: M2Model) -> List[M2Light]:
    return [light for light in model.lights if is_emitting_point_light(light)]


def authored_lamp(light: M2Light, kind: int, route: int, flags: int) -> ModelLamp:
    peak = peak_light_color(light)
    chroma = tuple(max(channel, 0.0) / peak for channel in light.diffuse_color)
    end = light.attenuation_end
    reach = end if math.isfinite(end) and end > 0.0 else DEFAULT_AUTHORED_REACH
    return ModelLamp(position=tuple(light.position), color=chroma, intensity=peak * light.diffuse_intensity,
                     reach=reach, kind=kind, route=route, flags=flags)


def box_extents(model: M2Model) -> Vec3:
    return tuple(high - low for low, high in zip(model.bounds_min, model.bounds_max))


def box_centre(model: M2Model) -> Vec3:
    return tuple((low + high) * 0.5 for low, high in zip(model.bounds_min, model.bounds_max))


def box_is_solid(model: M2Model) -> bool:
    extents = box_extents(model)
    return finite(extents) and min(extents) >= 0.0 and max(extents) > 0.0


def box_top_centre(model: M2Model) -> Vec3:
    centre = box_centre(model)
    return (centre[0], centre[1], model.bounds_max[2])


def extent_ratio_agrees(top: float, stock: float) -> bool:
    ratio = max(top, BOX_EXTENT_FLOOR) / max(stock, BOX_EXTENT_FLOOR)
    return RESTORE_MIN_EXTENT_RATIO <= ratio <= RESTORE_MAX_EXTENT_RATIO


def boxes_agree(top: M2Model, stock: M2Model) -> bool:
    offset = math.sqrt(sum((a - b) ** 2 for a, b in zip(box_centre(top), box_centre(stock))))
    return offset <= RESTORE_MAX_CENTRE_OFFSET and all(
        extent_ratio_agrees(a, b) for a, b in zip(box_extents(top), box_extents(stock)))


def peak_size(emitter: M2Emitter) -> float:
    return max([0.0] + list(emitter.sizes))


def peak_alpha(emitter: M2Emitter) -> float:
    return max(emitter.alphas) if emitter.alphas else 1.0


def key_alpha(emitter: M2Emitter, index: int) -> float:
    if not emitter.alphas:
        return 1.0
    if len(emitter.colors) < 2:
        return emitter.alphas[0]
    position = index / (len(emitter.colors) - 1)
    return emitter.alphas[int(position * (len(emitter.alphas) - 1) + 0.5)]


def peak_rate(emitter: M2Emitter) -> float:
    return emitter.emission_rate


def fire_emitter(emitter: M2Emitter) -> bool:
    return (fire_texture(emitter.texture) and emitter.blend in ADDITIVE_PARTICLE_BLENDS
            and peak_size(emitter) >= MIN_FLAME_SIZE and peak_rate(emitter) > 0.0
            and peak_alpha(emitter) >= VISIBLE_KEY_ALPHA)


def fire_strength(emitter: M2Emitter) -> float:
    return peak_size(emitter) * max(peak_rate(emitter), 0.0) ** RATE_ROOT


def fire_tier(strength: float) -> Tuple[float, int]:
    for limit, intensity, kind in FLAME_TIERS:
        if strength < limit:
            return intensity, kind
    return TOP_FLAME_TIER


def reach_for_intensity(intensity: float) -> float:
    for limit, reach in REACH_TIERS:
        if intensity < limit:
            return reach
    return TOP_REACH


def strongest_fire_emitter(emitters: Sequence[M2Emitter]) -> Optional[M2Emitter]:
    best = None
    best_strength = 0.0
    for emitter in emitters:
        if not fire_emitter(emitter):
            continue
        strength = fire_strength(emitter)
        if best is None or strength > best_strength:
            best, best_strength = emitter, strength
    return best


def saturation(color: Vec3) -> float:
    return max(color) - min(color)


def peak_normalized(color: Vec3) -> Optional[Vec3]:
    peak = max(color)
    if not peak > BLACK_PEAK:
        return None
    return tuple(channel / peak for channel in color)


def most_saturated(colors: Sequence[Vec3]) -> Optional[Vec3]:
    best = None
    for color in colors:
        if saturation(color) >= MIN_SATURATION and (best is None or saturation(color) >= saturation(best)):
            best = color
    return best


def visible_colors(emitter: M2Emitter) -> List[Vec3]:
    return [color for index, color in enumerate(emitter.colors) if key_alpha(emitter, index) >= VISIBLE_KEY_ALPHA]


def flame_color(emitter: M2Emitter) -> Vec3:
    best = most_saturated(visible_colors(emitter) or list(emitter.colors))
    normalized = None if best is None else peak_normalized(best)
    return DEFAULT_WARM if normalized is None else normalized


def is_cold(color: Vec3) -> bool:
    return color[0] < max(color[1], color[2])


def softened_cold_color(color: Vec3) -> Vec3:
    lowest = min(color)
    if not is_cold(color) or lowest >= COLD_COLOUR_FLOOR:
        return color
    toward_white = (COLD_COLOUR_FLOOR - lowest) / (1.0 - lowest)
    return tuple(channel + (1.0 - channel) * toward_white for channel in color)


def far_flame_margin(model: M2Model) -> float:
    return max(FAR_FLAME_MIN_MARGIN, FAR_FLAME_BOX_FRACTION * max(box_extents(model)))


def distance_outside(value: float, low: float, high: float) -> float:
    if not math.isfinite(value):
        return math.inf
    return max(low - value, 0.0, value - high)


def clamped_component(value: float, low: float, high: float) -> float:
    if not math.isfinite(value):
        return (low + high) * 0.5
    return min(max(value, low), high)


def clamped_into_box(model: M2Model, position: Vec3) -> Tuple[Vec3, bool]:
    if not box_is_solid(model):
        return position, False
    margin = far_flame_margin(model)
    bounds = list(zip(position, model.bounds_min, model.bounds_max))
    if all(distance_outside(value, low, high) <= margin for value, low, high in bounds):
        return position, False
    return tuple(clamped_component(value, low, high) for value, low, high in bounds), True


def flame_lamp(model: M2Model, flags: int) -> Optional[ModelLamp]:
    emitter = strongest_fire_emitter(model.emitters)
    if emitter is None:
        return None
    position, clamped = clamped_into_box(model, tuple(emitter.position))
    if not finite(position):
        return None
    intensity, kind = fire_tier(fire_strength(emitter))
    return ModelLamp(position=position, color=softened_cold_color(flame_color(emitter)), intensity=intensity,
                     reach=reach_for_intensity(intensity), kind=kind, route=ROUTE_FLAME,
                     flags=flags | (FLAG_CLAMPED_TO_MODEL if clamped else 0))


def lamp_color(path: str) -> Vec3:
    stem = basename_stem(path)
    for key, tint in NAME_TINTS:
        if key in stem:
            return tint
    return DEFAULT_LAMP if contains_any(stem, SHADED_LAMP_KEYS) else DEFAULT_WARM


def lamp_intensity(kind: Optional[int]) -> float:
    return LAMP_INTENSITIES.get(kind, GENERIC_LAMP_INTENSITY)


def is_glowing_transparent_batch(batch: M2Batch) -> bool:
    return batch.unlit and batch.blend in TRANSPARENT_BATCH_BLENDS and glow_texture(batch.texture)


def lamp_route(model: M2Model) -> Optional[int]:
    path = model.path
    if is_broken_or_off(path) or is_light_beam(path) or not lamp_family_ok(path):
        return None
    if lamp_kind(path) is not None:
        return ROUTE_NAME
    if in_lamp_dir(path) and any(is_glowing_transparent_batch(batch) for batch in model.batches):
        return ROUTE_EMISSIVE
    return None


def largest_unlit_batch(batches: Sequence[M2Batch], glow_only: bool) -> Optional[M2Batch]:
    best = None
    for batch in batches:
        if not batch.unlit or batch.index_count <= 0 or not finite(batch.center):
            continue
        if glow_only and not glow_texture(batch.texture):
            continue
        if best is None or batch.index_count >= best.index_count:
            best = batch
    return best


def lamp_position(model: M2Model, bounds_fallback: bool) -> Optional[Tuple[Vec3, int]]:
    batch = largest_unlit_batch(model.batches, True)
    if batch is None:
        batch = largest_unlit_batch(model.batches, False)
    if batch is not None:
        return tuple(batch.center), 0
    if not bounds_fallback or not box_is_solid(model):
        return None
    top = box_top_centre(model)
    return (top, FLAG_BOUNDS_FALLBACK) if finite(top) else None


def named_lamp(model: M2Model, flags: int) -> Optional[ModelLamp]:
    route = lamp_route(model)
    if route is None:
        return None
    kind = lamp_kind(model.path)
    placed = lamp_position(model, kind not in OPEN_FIRE_KINDS)
    if placed is None:
        return None
    position, position_flags = placed
    intensity = lamp_intensity(kind)
    return ModelLamp(position=position, color=lamp_color(model.path), intensity=intensity,
                     reach=reach_for_intensity(intensity), kind=KIND_LAMP if kind is None else kind, route=route,
                     flags=flags | position_flags)


def authored_kind(path: str) -> int:
    kind = lamp_kind(path)
    return KIND_LAMP if kind is None else kind


def restorable_lights(top: M2Model, stock: Optional[M2Model], notes: List[str]) -> List[M2Light]:
    if stock is None or stock is top:
        return []
    lights = emitting_point_lights(stock)
    if not lights:
        return []
    if not boxes_agree(top, stock):
        notes.append(NOTE_BOXES_DIFFER)
        return []
    return lights


def lamp_notes(lamp: ModelLamp) -> List[str]:
    notes = []
    if lamp.flags & FLAG_CLAMPED_TO_MODEL:
        notes.append(NOTE_FLAME_CLAMPED)
    if lamp.flags & FLAG_BOUNDS_FALLBACK:
        notes.append(NOTE_BOUNDS_FALLBACK)
    return notes


def synthesized_lamp(top: M2Model, flags: int) -> Optional[ModelLamp]:
    lamp = flame_lamp(top, flags)
    return lamp if lamp is not None else named_lamp(top, flags)


def classify(top: M2Model, stock: Optional[M2Model] = None) -> ModelVerdict:
    if is_spell_path(top.path):
        return ModelVerdict(route=None, notes=[NOTE_SPELL_EFFECT])
    kind = authored_kind(top.path)
    authored = emitting_point_lights(top)
    if authored:
        return ModelVerdict(route=ROUTE_AUTHORED,
                            lamps=[authored_lamp(light, kind, ROUTE_AUTHORED, 0) for light in authored])
    notes: List[str] = []
    flags = 0
    if top.lights:
        notes.append(NOTE_DEAD_BLOCKS)
        flags = FLAG_DEAD_AUTHORED_BLOCKS
    restored = restorable_lights(top, stock, notes)
    if restored:
        return ModelVerdict(route=ROUTE_RESTORED,
                            lamps=[authored_lamp(light, kind, ROUTE_RESTORED, flags) for light in restored],
                            notes=notes)
    if any(is_live_block(light) for light in top.lights):
        notes.append(NOTE_LIVE_NON_POINT_LIGHT)
        return ModelVerdict(route=None, notes=notes)
    lamp = synthesized_lamp(top, flags)
    if lamp is None:
        return ModelVerdict(route=None, notes=notes)
    return ModelVerdict(route=lamp.route, lamps=[lamp], notes=notes + lamp_notes(lamp))
