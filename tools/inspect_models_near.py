import argparse
import math
import ntpath
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, TextIO, Tuple

from extract_lamps import kind_of_source, model_path, read_maps, replace_unprintable, report_chain, say, vector
from lamp_census import counted
from lamp_formats import WDT_GRID, FormatError, Modf, WmoRoot, parse_adt, parse_wdt, parse_wmo_root, skin_path
from lamp_mpq import ArchiveChain, MpqError, VersionRead, read_archive_order
from lamp_types import FLAG_GLOBAL_WMO, Placement, Vec3
from lamp_world import (ADT_TILE_SIZE, DEFAULT_DOODAD_SET, MAP_ORIGIN, READ_ERRORS, WMO_DOODAD_ID_SHIFT, adt_name,
                        finite_values, model_key, placement_from_mddf, placement_from_modf, placement_world_position,
                        present_reads, read_adt_prefix, wdt_name, wmo_doodad_placements)
from model_materials import (NO_COLOR, M2Materials, RenderBatch, TrackKeys, WmoDetails, WorldMapArea,
                             WORLD_MAP_AREA_FIELDS, WORLD_MAP_AREA_RECORD_SIZE, entry, parse_m2_materials,
                             parse_wmo_details, parse_world_map_area_dbc)

PROGRAM = "inspect_models_near.py"
WORLD_MAP_AREA_DBC = "DBFilesClient\\WorldMapArea.dbc"
EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
INDENT = "  "
PAIR_SEPARATOR = ","
DEFAULT_RADIUS = 40.0
MAX_RADIUS = 1000.0
PERCENT = 100.0
WMO_SUFFIX = ".wmo"
DOODAD_INDEX_MASK = (1 << WMO_DOODAD_ID_SHIFT) - 1

LAST_PASS_ZERO_BLEND = 1
OPAQUE_ALPHA = 0.99999
FOG_MODE_BY_BLEND = (1, 1, 1, 2, 2, 3, 4, 0)
FOG_MODE_NAMES = {0: "unfogged", 1: "the lighting's fog colour", 2: "black", 3: "white", 4: "grey 0x80"}
BLEND_NAMES = ("opaque", "alpha key", "alpha", "no-alpha add", "add", "modulate", "modulate 2x", "blend add")
MATERIAL_UNFOGGED = 0x2
M2_MATERIAL_FLAGS = ((0x1, "unlit"), (0x2, "unfogged"), (0x4, "two-sided"), (0x8, "no depth test"),
                     (0x10, "no depth write"))
WMO_MATERIAL_FLAGS = ((0x1, "unlit"), (0x2, "unfogged"), (0x4, "two-sided"), (0x8, "exterior light"),
                      (0x10, "night glow"), (0x20, "window"), (0x40, "clamp s"), (0x80, "clamp t"))
ENVIRONMENT_COORDINATES = -1

LEGEND = ("client treatment, predicted from the files: a batch goes to the see-through pass when its blend mode is "
          "above 1 or its colour alpha x transparency is below 0.99999, otherwise to pass 0; its stock fog mode "
          "follows the blend mode through {1,1,1,2,2,3,4,0} (1 the lighting's fog colour, 2 black, 3 white, 4 grey, "
          "0 unfogged) and is 0 when the material has flag 0x2 or the lighting has no fog. A model fading in or out, "
          "the lighting and LuxVelum's settings are not known here; distances are horizontal.")


@dataclass
class Point:
    label: str
    map_id: int
    directory: str
    x: float
    y: float


@dataclass
class NearbyM2:
    placement: Placement
    distance: float
    origin: str


@dataclass
class NearbyWmo:
    placement: Placement
    distance: float
    box_min: Vec3
    box_max: Vec3
    origin: str


@dataclass
class Survey:
    point: Point
    tiles: List[str] = field(default_factory=list)
    m2s: List[NearbyM2] = field(default_factory=list)
    wmos: List[NearbyWmo] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ModelFile:
    versions: List[str]
    skin: Optional[str] = None
    materials: Optional[M2Materials] = None
    problem: Optional[str] = None


@dataclass
class WmoFile:
    versions: List[str]
    root: Optional[WmoRoot] = None
    details: Optional[WmoDetails] = None
    problem: Optional[str] = None


def coordinate_pairs(text: str, example: str, what: str) -> List[Tuple[float, float]]:
    parts = [part for part in text.replace(" ", PAIR_SEPARATOR).split(PAIR_SEPARATOR) if part]
    try:
        values = [float(part) for part in parts]
    except ValueError:
        values = []
    if not values or len(values) % 2 or not finite_values(values):
        raise argparse.ArgumentTypeError("%r is not %s x,y such as %s (a dot for decimals)" % (text, what, example))
    return list(zip(values[0::2], values[1::2]))


def zone_points(text: str) -> List[Tuple[float, float]]:
    return coordinate_pairs(text, "26.4,38.5", "a zone coordinate in percent")


def world_points(text: str) -> List[Tuple[float, float]]:
    return coordinate_pairs(text, "3193.1,177.6", "a world position in yards")


class PointsAction(argparse.Action):
    def __init__(self, option_strings, dest, parse=None, **kwargs):
        self.parse = parse
        super().__init__(option_strings, dest, nargs="+", **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            points = self.parse(" ".join(values))
        except argparse.ArgumentTypeError as error:
            raise argparse.ArgumentError(self, str(error)) from None
        setattr(namespace, self.dest, list(getattr(namespace, self.dest) or []) + points)


def radius_value(text: str) -> float:
    try:
        radius = float(text)
    except ValueError:
        radius = math.nan
    if not 0.0 < radius <= MAX_RADIUS:
        raise argparse.ArgumentTypeError("%r is not a radius above 0 and at most %d yd" % (text, MAX_RADIUS))
    return radius


def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM, description="Lists the models the client's map files place near a point, nearest first, with "
                                  "the render materials of every batch and how the client draws and fogs it.")
    parser.add_argument("--data", required=True, help="the client's Data folder")
    parser.add_argument("--zone", help="the zone as WorldMapArea.dbc names it, such as Ashenvale")
    parser.add_argument("--at", action=PointsAction, parse=zone_points, metavar="X,Y",
                        help="zone coordinates in percent as the world map shows them, such as 26.4,38.5; "
                             "more pairs give more points")
    parser.add_argument("--map", type=int, help="map id, such as 1 for Kalimdor")
    parser.add_argument("--world", action=PointsAction, parse=world_points, metavar="X,Y",
                        help="world position in yards on --map, such as 3193.1,177.6 (--world=-1234.5,67.8 "
                             "when x is negative); more pairs give more points")
    parser.add_argument("--radius", type=radius_value, default=DEFAULT_RADIUS,
                        help="horizontal distance in yards (default %d)" % DEFAULT_RADIUS)
    parser.add_argument("--locale", help="locale folder in Data, such as enUS (default: found from its archives)")
    parser.add_argument("--archives", help="text file naming the archives to read, one path relative to the Data "
                                           "folder per line, lowest priority first (default: the client's order)")
    parser.add_argument("--model", nargs="+", metavar="PATH",
                        help="describe these M2 or WMO files instead of the models near a point")
    return parser


def point_problem(args: argparse.Namespace) -> Optional[str]:
    by_zone = args.zone is not None or args.at is not None
    by_world = args.map is not None or args.world is not None
    if args.model:
        return "--model describes files and takes no point" if by_zone or by_world else None
    if by_zone and by_world:
        return "give either --zone with --at or --map with --world"
    if by_zone and (args.zone is None or args.at is None):
        return "--zone and --at go together"
    if by_world and (args.map is None or args.world is None):
        return "--map and --world go together"
    if not by_zone and not by_world:
        return "give --zone with --at, --map with --world, or --model"
    return None


def usage_problem(args: argparse.Namespace) -> Optional[str]:
    if not os.path.isdir(args.data):
        return "--data %s is not a folder" % args.data
    problem = point_problem(args)
    if problem is not None or args.archives is None:
        return problem
    try:
        read_archive_order(args.archives, args.data)
    except (MpqError, OSError, UnicodeDecodeError) as error:
        return "--archives: %s" % error
    return None


def zone_to_world(area: WorldMapArea, percent_x: float, percent_y: float) -> Tuple[float, float]:
    return (area.top + percent_y / PERCENT * (area.bottom - area.top),
            area.left + percent_x / PERCENT * (area.right - area.left))


def zone_key(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalnum())


def flag_text(flags: int, names: Sequence[Tuple[int, str]]) -> str:
    named = [name for bit, name in names if flags & bit]
    rest = flags & ~sum(bit for bit, _ in names)
    if rest:
        named.append("0x%X unnamed" % rest)
    return "0x%X (%s)" % (flags, ", ".join(named)) if named else "0x0"


def blend_text(blend: int) -> str:
    name = entry(BLEND_NAMES, blend)
    return "%d (%s)" % (blend, name) if name else "%d (outside the 8 blend modes)" % blend


def version_label(read: VersionRead) -> str:
    label = "%s (%s)" % (read.source.name, kind_of_source(read.source))
    return label + ", unreadable" if read.error is not None else label


def top_skin(chain: ArchiveChain, name: Optional[str]) -> Tuple[Optional[str], Optional[bytes], Optional[str]]:
    try:
        reads = present_reads(chain, name)
    except MpqError as error:
        return None, None, "skin unreadable: %s" % error
    if not reads:
        return None, None, None
    if reads[0].error is not None:
        return version_label(reads[0]), None, "skin unreadable: %s" % reads[0].error
    return version_label(reads[0]), reads[0].data, None


def read_model_file(chain: ArchiveChain, key: str) -> ModelFile:
    try:
        reads = present_reads(chain, key)
    except MpqError as error:
        return ModelFile([], problem="unreadable: %s" % error)
    if not reads:
        return ModelFile([], problem="missing file")
    model = ModelFile([version_label(read) for read in reads])
    if reads[0].error is not None:
        model.problem = "unreadable: %s" % reads[0].error
        return model
    model.skin, skin, skin_problem = top_skin(chain, skin_path(key))
    try:
        model.materials = parse_m2_materials(key, reads[0].data, skin)
    except FormatError as error:
        model.problem = "parse error: %s" % error
        return model
    if skin_problem:
        model.materials.notes.append(skin_problem)
    return model


def read_wmo_file(chain: ArchiveChain, key: str) -> WmoFile:
    try:
        reads = present_reads(chain, key)
    except MpqError as error:
        return WmoFile([], problem="unreadable: %s" % error)
    if not reads:
        return WmoFile([], problem="missing file")
    wmo = WmoFile([version_label(read) for read in reads])
    if reads[0].error is not None:
        wmo.problem = "unreadable: %s" % reads[0].error
        return wmo
    try:
        wmo.root = parse_wmo_root(reads[0].data, key)
        wmo.details = parse_wmo_details(reads[0].data, key)
    except FormatError as error:
        wmo.problem = "parse error: %s" % error
    return wmo


class Files:
    def __init__(self, chain: ArchiveChain):
        self.chain = chain
        self.models: Dict[str, ModelFile] = {}
        self.wmos: Dict[str, WmoFile] = {}

    def model(self, name: str) -> ModelFile:
        key = model_key(name)
        if key not in self.models:
            self.models[key] = read_model_file(self.chain, key)
        return self.models[key]

    def wmo(self, name: str) -> WmoFile:
        key = model_key(name)
        if key not in self.wmos:
            self.wmos[key] = read_wmo_file(self.chain, key)
        return self.wmos[key]


def tiles_near(x: float, y: float, radius: float) -> List[Tuple[int, int]]:
    def span(centre: float) -> range:
        low = math.floor((MAP_ORIGIN - (centre + radius)) / ADT_TILE_SIZE)
        high = math.floor((MAP_ORIGIN - (centre - radius)) / ADT_TILE_SIZE)
        return range(max(low, 0), min(high, WDT_GRID - 1) + 1)
    return [(tile_x, tile_y) for tile_y in span(x) for tile_x in span(y)]


def horizontal_distance(position: Vec3, point: Point) -> float:
    return math.hypot(position[0] - point.x, position[1] - point.y)


def world_box(wmo: Modf) -> Tuple[Vec3, Vec3]:
    corners = [placement_world_position(wmo.extents_min), placement_world_position(wmo.extents_max)]
    return (tuple(min(corner[axis] for corner in corners) for axis in range(3)),
            tuple(max(corner[axis] for corner in corners) for axis in range(3)))


def box_distance(box_min: Vec3, box_max: Vec3, point: Point) -> float:
    return math.hypot(max(box_min[0] - point.x, 0.0, point.x - box_max[0]),
                      max(box_min[1] - point.y, 0.0, point.y - box_max[1]))


def doodad_set_labels(root: WmoRoot, doodad_set: int) -> Dict[int, str]:
    labels: Dict[int, str] = {}
    for set_index in dict.fromkeys((DEFAULT_DOODAD_SET, doodad_set)):
        chosen = entry(root.doodad_sets, set_index)
        if chosen is None:
            continue
        for index in range(chosen.start, min(chosen.start + chosen.count, len(root.doodads))):
            labels.setdefault(index, "%d %s" % (set_index, chosen.name))
    return labels


class Surveyor:
    def __init__(self, files: Files, radius: float):
        self.files = files
        self.radius = radius

    def survey(self, point: Point) -> Survey:
        survey = Survey(point)
        try:
            data = self.files.chain.read(wdt_name(point.directory))
            wdt = parse_wdt(data) if data else None
        except READ_ERRORS as error:
            survey.notes.append("%s is unreadable: %s" % (wdt_name(point.directory), error))
            return survey
        if wdt is None:
            survey.notes.append("no %s in any archive" % wdt_name(point.directory))
            return survey
        present = set(wdt.tiles)
        seen: Dict[str, set] = {"m2": set(), "wmo": set()}
        for tile in tiles_near(point.x, point.y, self.radius):
            self.walk_tile(survey, tile, tile in present, seen)
        if wdt.global_wmo_placement is not None:
            self.add_wmo(survey, wdt.global_wmo_placement, FLAG_GLOBAL_WMO, "WDT (global WMO)")
        survey.m2s.sort(key=lambda found: (found.distance, found.placement.model))
        survey.wmos.sort(key=lambda found: (found.distance, found.placement.model))
        return survey

    def walk_tile(self, survey: Survey, tile: Tuple[int, int], present: bool, seen: Dict[str, set]) -> None:
        name = adt_name(survey.point.directory, *tile)
        short = ntpath.basename(name)
        if not present:
            survey.tiles.append("%s: not in the WDT" % short)
            return
        try:
            prefix = read_adt_prefix(self.files.chain, name)
            adt = parse_adt(prefix) if prefix else None
        except READ_ERRORS as error:
            survey.tiles.append("%s: unreadable (%s)" % (short, error))
            return
        if adt is None:
            survey.tiles.append("%s: missing" % short)
            return
        survey.tiles.append("%s: %s, %s" % (short, counted(len(adt.doodads), "M2 placement"),
                                             counted(len(adt.wmos), "WMO placement")))
        for doodad in adt.doodads:
            if doodad.unique_id in seen["m2"]:
                continue
            seen["m2"].add(doodad.unique_id)
            if not finite_values(tuple(doodad.position) + tuple(doodad.rotation)):
                survey.notes.append("%s: M2 placement %d is not finite" % (short, doodad.unique_id))
                continue
            placement = placement_from_mddf(doodad)
            distance = horizontal_distance(placement.position, survey.point)
            if distance <= self.radius:
                origin = "placed by %s (MDDF), unique id %d, rotation %s, scale %.2f, flags 0x%X" % (
                    short, doodad.unique_id, angles(doodad.rotation), placement.scale, doodad.flags)
                survey.m2s.append(NearbyM2(placement, distance, origin))
        for wmo in adt.wmos:
            if wmo.unique_id not in seen["wmo"]:
                seen["wmo"].add(wmo.unique_id)
                self.add_wmo(survey, wmo, 0, "%s (MODF)" % short)

    def add_wmo(self, survey: Survey, wmo: Modf, flags: int, origin: str) -> None:
        if not wmo.name or not finite_values(tuple(wmo.position) + tuple(wmo.rotation)):
            survey.notes.append("%s: WMO placement %d is nameless or not finite" % (origin, wmo.unique_id))
            return
        placement = placement_from_modf(wmo, flags)
        box_min, box_max = world_box(wmo)
        distance = min(box_distance(box_min, box_max, survey.point), horizontal_distance(placement.position,
                                                                                         survey.point))
        if distance <= self.radius or flags & FLAG_GLOBAL_WMO:
            placed = "placed by %s, unique id %d, rotation %s, doodad set %d, flags 0x%X" % (
                origin, wmo.unique_id, angles(wmo.rotation), wmo.doodad_set, wmo.flags)
            survey.wmos.append(NearbyWmo(placement, distance, box_min, box_max, placed))
        root = self.files.wmo(wmo.name).root
        if root is None:
            return
        labels = doodad_set_labels(root, wmo.doodad_set)
        for doodad in wmo_doodad_placements(placement, root, wmo.doodad_set):
            distance = horizontal_distance(doodad.position, survey.point)
            if distance > self.radius:
                continue
            index = doodad.unique_id & DOODAD_INDEX_MASK
            placed = "placed by WMO %s (unique id %d), doodad set %s, doodad %d, scale %.2f" % (
                wmo.name, wmo.unique_id, labels.get(index, "?"), index, doodad.scale)
            survey.m2s.append(NearbyM2(doodad, distance, placed))


def angles(values: Sequence[float]) -> str:
    return "(%s)" % ", ".join("%.1f" % value for value in values)


def alpha_text(value: float) -> str:
    text = "%.3f" % value
    if text == "1.000" and value < OPAQUE_ALPHA:
        return "%.5f" % value
    return text


def keys_tail(keys: TrackKeys) -> str:
    tail = ""
    if keys.external_sequences:
        tail += ", %s in .anim files not read" % counted(keys.external_sequences, "sequence")
    if keys.outside_file:
        tail += ", %s outside the file" % counted(keys.outside_file, "key array")
    return tail


def scalar_keys_text(keys: TrackKeys) -> str:
    if not keys.values:
        return "no keys" + keys_tail(keys)
    low, high = min(keys.values), max(keys.values)
    if low == high:
        return "%s static" % alpha_text(low) + keys_tail(keys)
    return "%s to %s animated (%s)" % (alpha_text(low), alpha_text(high),
                                       counted(len(keys.values), "key")) + keys_tail(keys)


def colour_keys_text(keys: TrackKeys) -> str:
    if not keys.values:
        return "no keys" + keys_tail(keys)
    low = tuple(min(value[axis] for value in keys.values) for axis in range(3))
    high = tuple(max(value[axis] for value in keys.values) for axis in range(3))
    if low == high:
        return "%s static" % vector(low) + keys_tail(keys)
    return "%s to %s animated (%s)" % (vector(low), vector(high), counted(len(keys.values), "key")) + keys_tail(keys)


def value_range(keys: Optional[TrackKeys]) -> Tuple[float, float]:
    if keys is None or not keys.values:
        return 1.0, 1.0
    return min(keys.values), max(keys.values)


def alpha_range(batch: RenderBatch) -> Tuple[float, float]:
    alpha_low, alpha_high = value_range(batch.color_alpha)
    weight_low, weight_high = value_range(batch.transparency)
    products = [alpha * weight for alpha in (alpha_low, alpha_high) for weight in (weight_low, weight_high)]
    return min(products), max(products)


def pass_text(batch: RenderBatch) -> str:
    if batch.blend is None:
        return "pass unknown (no material)"
    if batch.blend > LAST_PASS_ZERO_BLEND:
        return "see-through pass (blend %d above 1)" % batch.blend
    low, high = alpha_range(batch)
    if high < OPAQUE_ALPHA:
        return "see-through pass (alpha %s below 0.99999)" % alpha_text(high)
    if low < OPAQUE_ALPHA:
        return "pass 0 or the see-through pass as its alpha animates (%s to %s)" % (alpha_text(low),
                                                                                  alpha_text(high))
    return "pass 0"


def fog_text(batch: RenderBatch) -> str:
    if batch.material_flags is None:
        return "stock fog mode unknown (no material)"
    if batch.material_flags & MATERIAL_UNFOGGED:
        return "stock fog mode 0 (unfogged: material flag 0x2)"
    mode = entry(FOG_MODE_BY_BLEND, batch.blend)
    if mode is None:
        return "stock fog mode unknown (blend %d is outside the table of 8)" % batch.blend
    return "stock fog mode %d (%s)" % (mode, FOG_MODE_NAMES[mode])


def texture_text(batch_texture) -> str:
    texture = batch_texture.texture
    if texture is None:
        name = "(outside the table)"
    elif texture.name:
        name = texture.name
    else:
        name = "(replaceable type %d)" % texture.texture_type
    if batch_texture.coord is None:
        return name
    coordinates = "environment map" if batch_texture.coord == ENVIRONMENT_COORDINATES else "uv %d" % (
        batch_texture.coord)
    return "%s (%s)" % (name, coordinates)


def batch_lines(index: int, batch: RenderBatch) -> List[str]:
    indices = "?" if batch.index_count is None else str(batch.index_count)
    lines = ["batch %d: submesh %d (%s indices), priority plane %d, material layer %d, batch flags 0x%X" % (
        index, batch.submesh, indices, batch.priority, batch.layer, batch.flags)]
    if batch.blend is not None:
        lines.append(INDENT + "material %d: blend %s, flags %s" % (batch.material, blend_text(batch.blend),
                                                                    flag_text(batch.material_flags,
                                                                              M2_MATERIAL_FLAGS)))
    combos = ", combiner combos %s" % batch.combiner_combos if batch.combiner_combos else ""
    lines.append(INDENT + "shader 0x%X%s, %s: %s" % (batch.shader, combos, counted(batch.texture_count, "texture"),
                                                     "; ".join(texture_text(texture) for texture in batch.textures)))
    if batch.color == NO_COLOR:
        lines.append(INDENT + "colour none")
    elif batch.color_alpha is not None:
        lines.append(INDENT + "colour %d: rgb %s, alpha %s" % (batch.color, colour_keys_text(batch.color_rgb),
                                                               scalar_keys_text(batch.color_alpha)))
    if batch.transparency is not None:
        lines.append(INDENT + "transparency lookup %d -> weight %d: %s" % (
            batch.weight_lookup, batch.weight, scalar_keys_text(batch.transparency)))
    lines.append(INDENT + "client: %s, %s" % (pass_text(batch), fog_text(batch)))
    lines.extend(INDENT + "note: " + note for note in batch.notes)
    return lines


def materials_lines(materials: M2Materials) -> List[str]:
    lines = ["M2 version %d, global flags 0x%X, %s, box %s to %s, %s (%d in .anim files), %s" % (
        materials.version, materials.global_flags, counted(materials.skin_profiles, "skin profile"),
        vector(materials.bounds_min), vector(materials.bounds_max), counted(materials.sequences, "sequence"),
        materials.external_sequences, counted(len(materials.textures), "texture"))]
    lines.append("render batches in skin 00: %d" % len(materials.batches))
    for index, batch in enumerate(materials.batches):
        lines.extend(INDENT + line for line in batch_lines(index, batch))
    lines.extend("note: " + note for note in materials.notes)
    return lines


def model_file_lines(model: ModelFile) -> List[str]:
    lines = []
    if model.versions:
        lower = "; lower versions: " + ", ".join(model.versions[1:]) if len(model.versions) > 1 else ""
        lines.append("file: %s%s" % (model.versions[0], lower))
    if model.materials is not None:
        if model.skin is not None:
            same = model.skin.split(" (")[0] == model.versions[0].split(" (")[0]
            lines.append("skin 00: %s%s" % (model.skin, "" if same else ", another archive than the model"))
        lines.extend(materials_lines(model.materials))
    if model.problem:
        lines.append(model.problem)
    return lines


def wmo_material_line(index: int, material) -> str:
    return "material %d: blend %s, flags %s, shader %d, sidn 0x%08X, diffuse 0x%08X, textures %s" % (
        index, blend_text(material.blend), flag_text(material.flags, WMO_MATERIAL_FLAGS), material.shader,
        material.sidn_color, material.diffuse_color, ", ".join(material.textures) or "none")


def wmo_fog_line(index: int, fog) -> str:
    return ("fog %d: flags 0x%X, at %s, radius %.1f to %.1f, end %.1f, start x%.2f, colour 0x%08X, under water end "
            "%.1f, start x%.2f, colour 0x%08X" % (index, fog.flags, vector(fog.position), fog.small_radius,
                                                  fog.large_radius, fog.end, fog.start_factor, fog.color,
                                                  fog.underwater_end, fog.underwater_start_factor,
                                                  fog.underwater_color))


def wmo_file_lines(wmo: WmoFile) -> List[str]:
    lines = []
    if wmo.versions:
        lower = "; lower versions: " + ", ".join(wmo.versions[1:]) if len(wmo.versions) > 1 else ""
        lines.append("file: %s%s" % (wmo.versions[0], lower))
    if wmo.details is not None:
        details = wmo.details
        lines.append("WMO header flags 0x%X, %s, ambient 0x%08X, %s, %s" % (
            details.flags, counted(details.groups, "group"), details.ambient_color,
            counted(len(details.materials), "material"), counted(len(details.fogs), "fog")))
        lines.extend(wmo_material_line(index, material) for index, material in enumerate(details.materials))
        lines.extend(wmo_fog_line(index, fog) for index, fog in enumerate(details.fogs))
    if wmo.root is not None:
        sets = ["%d %s (%s)" % (index, doodads.name, counted(doodads.count, "doodad"))
                for index, doodads in enumerate(wmo.root.doodad_sets)]
        lines.append("doodad sets: " + ("; ".join(sets) or "none"))
    if wmo.problem:
        lines.append(wmo.problem)
    return lines


class Report:
    def __init__(self, files: Files, out: TextIO):
        self.files = files
        self.out = out
        self.described: Dict[str, str] = {}

    def lines(self, lines: Sequence[str]) -> None:
        for line in lines:
            say(self.out, INDENT + line)

    def first_description(self, key: str, label: str) -> Optional[str]:
        if key in self.described:
            return self.described[key]
        self.described[key] = label
        return None

    def m2(self, label: str, found: NearbyM2) -> None:
        position = found.placement.position
        say(self.out, "%s M2 %s" % (label, found.placement.model or "(nameless)"))
        self.lines(["%.1f yd away at %s" % (found.distance, vector(position)), found.origin])
        if not found.placement.model:
            return
        earlier = self.first_description("m2:" + model_key(found.placement.model), label)
        if earlier is not None:
            self.lines(["same model as %s" % earlier])
            return
        self.lines(model_file_lines(self.files.model(found.placement.model)))

    def wmo(self, label: str, found: NearbyWmo) -> None:
        say(self.out, "%s WMO %s" % (label, found.placement.model))
        self.lines(["%.1f yd away, at %s, box %s to %s" % (found.distance, vector(found.placement.position),
                                                           vector(found.box_min), vector(found.box_max)),
                    found.origin])
        earlier = self.first_description("wmo:" + model_key(found.placement.model), label)
        if earlier is not None:
            self.lines(["same WMO as %s" % earlier])
            return
        self.lines(wmo_file_lines(self.files.wmo(found.placement.model)))

    def survey(self, survey: Survey, radius: float) -> None:
        point = survey.point
        say(self.out, "")
        say(self.out, "point %s: world (%.2f, %.2f) on map %d %s, within %.1f yd" % (
            point.label, point.x, point.y, point.map_id, point.directory, radius))
        say(self.out, "tiles: " + ("; ".join(survey.tiles) or "none"))
        for note in survey.notes:
            say(self.out, "note: " + note)
        say(self.out, "M2 models within %.1f yd of point %s, nearest first: %d" % (radius, point.label,
                                                                                 len(survey.m2s)))
        for index, found in enumerate(survey.m2s, 1):
            self.m2("point %s #%d" % (point.label, index), found)
        say(self.out, "WMOs within %.1f yd of point %s, nearest first: %d" % (radius, point.label, len(survey.wmos)))
        for index, found in enumerate(survey.wmos, 1):
            self.wmo("point %s WMO #%d" % (point.label, index), found)
        if not survey.m2s and not survey.wmos:
            say(self.out, "nothing placed there: server-spawned objects and creatures are not in the map files")


def common_models(surveys: Sequence[Survey]) -> List[Tuple[str, List[Tuple[int, float]]]]:
    nearest: Dict[str, List[Optional[Tuple[int, float]]]] = {}
    names: Dict[str, str] = {}
    for column, survey in enumerate(surveys):
        for index, found in enumerate(survey.m2s, 1):
            key = model_key(found.placement.model)
            names.setdefault(key, found.placement.model)
            row = nearest.setdefault(key, [None] * len(surveys))
            if row[column] is None:
                row[column] = (index, found.distance)
    return [(names[key], row) for key, row in nearest.items() if all(cell is not None for cell in row)]


def report_common(surveys: Sequence[Survey], out: TextIO) -> None:
    if len(surveys) < 2:
        return
    common = common_models(surveys)
    say(out, "")
    say(out, "M2 models near every point: %d" % len(common))
    for name, row in common:
        say(out, INDENT + "%s: %s" % (name, "; ".join("point %s #%d at %.1f yd" % (survey.point.label, index,
                                                                                   distance)
                                                      for survey, (index, distance) in zip(surveys, row))))


def read_world_map_areas(chain: ArchiveChain, out: TextIO):
    try:
        data = chain.read(WORLD_MAP_AREA_DBC)
        if data is None:
            say(out, "no %s in any archive" % WORLD_MAP_AREA_DBC)
            return None
        return parse_world_map_area_dbc(data)
    except (MpqError, FormatError) as error:
        say(out, "%s is unreadable: %s" % (WORLD_MAP_AREA_DBC, error))
        return None


def zone_area(chain: ArchiveChain, name: str, out: TextIO) -> Optional[WorldMapArea]:
    table = read_world_map_areas(chain, out)
    if table is None:
        return None
    if table.fields != WORLD_MAP_AREA_FIELDS or table.record_size != WORLD_MAP_AREA_RECORD_SIZE:
        say(out, "note: WorldMapArea.dbc has %d fields in %d bytes, not 11 in 44; read as 3.3.5a's ID, map, area, "
                 "name, left, right, top, bottom" % (table.fields, table.record_size))
    matches = [area for area in table.areas if zone_key(area.name) == zone_key(name)]
    if not matches:
        say(out, "no zone %s in WorldMapArea.dbc; its names: %s" % (
            name, ", ".join(sorted({area.name for area in table.areas}, key=str.lower))))
        return None
    area = matches[0]
    say(out, "zone %s: WorldMapArea %d, map %d, area %d, left %.2f, right %.2f, top %.2f, bottom %.2f" % (
        area.name, area.record_id, area.map_id, area.area_id, area.left, area.right, area.top, area.bottom))
    for other in matches[1:]:
        say(out, "note: WorldMapArea %d on map %d has the same name and is not used" % (other.record_id,
                                                                                      other.map_id))
    if area.left == area.right or area.top == area.bottom:
        say(out, "zone %s has no extent on the world map" % area.name)
        return None
    return area


def resolve_points(chain: ArchiveChain, args: argparse.Namespace, out: TextIO) -> Optional[List[Point]]:
    maps = read_maps(chain, out)
    if maps is None:
        return None
    directories = dict(maps)
    if args.zone is not None:
        area = zone_area(chain, args.zone, out)
        if area is None:
            return None
        map_id = area.map_id
        positions = [zone_to_world(area, *percent) for percent in args.at]
        sources = ["%.1f, %.1f in %s" % (percent[0], percent[1], area.name) for percent in args.at]
    else:
        map_id = args.map
        positions = list(args.world)
        sources = ["world %.2f, %.2f" % position for position in args.world]
    if map_id not in directories:
        say(out, "map %d is not in DBFilesClient\\Map.dbc" % map_id)
        return None
    points = [Point(str(index), map_id, directories[map_id], x, y) for index, (x, y) in enumerate(positions, 1)]
    for point, source in zip(points, sources):
        say(out, "point %s: %s -> world (%.2f, %.2f) on map %d %s" % (point.label, source, point.x, point.y,
                                                                       point.map_id, point.directory))
    return points


def describe_files(files: Files, paths: Sequence[str], out: TextIO) -> int:
    for text in paths:
        path = model_path(text.replace("/", "\\"))
        if path.lower().endswith(WMO_SUFFIX):
            say(out, "WMO " + path)
            lines = wmo_file_lines(files.wmo(path))
        else:
            say(out, "M2 " + path)
            lines = model_file_lines(files.model(path))
        for line in lines:
            say(out, INDENT + line)
    return EXIT_OK


def inspect(chain: ArchiveChain, args: argparse.Namespace, out: TextIO) -> int:
    files = Files(chain)
    say(out, LEGEND)
    if args.model:
        return describe_files(files, args.model, out)
    points = resolve_points(chain, args, out)
    if points is None:
        return EXIT_NOT_FOUND
    surveyor = Surveyor(files, args.radius)
    report = Report(files, out)
    surveys = []
    for point in points:
        survey = surveyor.survey(point)
        report.survey(survey, args.radius)
        surveys.append(survey)
    report_common(surveys, out)
    return EXIT_OK


def run(args: argparse.Namespace, out: TextIO) -> int:
    try:
        chain = ArchiveChain(args.data, locale=args.locale, order_file=args.archives)
    except (MpqError, OSError) as error:
        say(out, "cannot open the archives: %s" % error)
        return EXIT_NOT_FOUND
    with chain:
        report_chain(chain, out)
        if not chain.sources:
            say(out, ("no MPQ archive in %s could be opened" if chain.unreadable else "no MPQ archive found in %s")
                % args.data)
            return EXIT_NOT_FOUND
        return inspect(chain, args, out)


def main(argv: Optional[Sequence[str]] = None, out: Optional[TextIO] = None) -> int:
    parser = argument_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else EXIT_USAGE
    problem = usage_problem(args)
    if problem is not None:
        parser.print_usage(sys.stderr)
        print("%s: error: %s" % (PROGRAM, problem), file=sys.stderr)
        return EXIT_USAGE
    return run(args, out or sys.stdout)


if __name__ == "__main__":
    replace_unprintable(sys.stdout)
    sys.exit(main())
