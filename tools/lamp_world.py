import itertools
import math
import string
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from lamp_formats import (ADT_HEADER_SIZE, FormatError, Mddf, Modf, WmoRoot, adt_prefix_size, m2_light_count,
                          parse_adt, parse_m2, parse_wdt, parse_wmo_root, skin_path)
from lamp_mpq import MpqError, VersionRead
from lamp_math import (add, diagonal, distance_squared, multiply, quaternion_matrix, rotation_x, rotation_y,
                       rotation_z, scaled, transform)
from lamp_types import FLAG_GLOBAL_WMO, FLAG_WMO_DOODAD, Lamp, M2Model, Matrix3, ModelVerdict, Placement, Vec3

ADT_TILE_SIZE = 533.33333
MAP_ORIGIN = 32 * ADT_TILE_SIZE
WORLD_FLIP: Matrix3 = diagonal((-1.0, -1.0, 1.0))
MDDF_SCALE_ONE = 1024.0
WMO_DOODAD_ID_SHIFT = 32
DEFAULT_DOODAD_SET = 0
LAMP_MERGE_DISTANCE = 0.5
MAX_PREFIX_ROUNDS = 8

PLACEMENT_M2 = "m2"
PLACEMENT_WMO = "wmo"
FILE_WDT = "wdt"
FILE_ADT = "adt"
FILE_WMO = "wmo"
FILE_M2 = "m2"
NAMELESS = "nameless"
NOT_FINITE = "placement"
NOTE_MISSING_FILE = "missing file"
LOWER_VERSION_LABEL = "lower version "
SKIN_LABEL = "skin "
READ_ERRORS = (FormatError, MpqError)
MODEL_KEY_FOLD = str.maketrans(string.ascii_lowercase + "/", string.ascii_uppercase + "\\")

Classify = Callable[[M2Model, Optional[M2Model]], ModelVerdict]


@dataclass
class MapCensus:
    map_id: int
    directory: str
    tiles: int = 0
    placements: int = 0
    wmo_placements: int = 0
    lamps: int = 0
    routes: Dict[int, int] = field(default_factory=dict)
    missing: Dict[str, int] = field(default_factory=dict)
    errors: Dict[str, int] = field(default_factory=dict)


@dataclass
class ModelCensus:
    path: str
    archives: List[str] = field(default_factory=list)
    version_lights: List[Optional[int]] = field(default_factory=list)
    top_lights: int = 0
    stock_lights: int = 0
    route: Optional[int] = None
    notes: List[str] = field(default_factory=list)
    placements: Dict[int, int] = field(default_factory=dict)

    @property
    def light_blocks(self) -> bool:
        return any(self.version_lights)

    @property
    def lamp_like(self) -> bool:
        return self.route is not None

    @property
    def total_placements(self) -> int:
        return sum(self.placements.values())


@dataclass
class Census:
    maps: Dict[int, MapCensus] = field(default_factory=dict)
    models: Dict[str, ModelCensus] = field(default_factory=dict)

    def map(self, map_id: int, directory: str) -> MapCensus:
        if map_id not in self.maps:
            self.maps[map_id] = MapCensus(map_id, directory)
        return self.maps[map_id]

    def notable_models(self) -> List[ModelCensus]:
        notable = [model for model in self.models.values() if model.lamp_like or model.light_blocks]
        return sorted(notable, key=lambda model: (-model.total_placements, model.path))


def count(counter: Dict, key) -> None:
    counter[key] = counter.get(key, 0) + 1


def model_key(path: str) -> str:
    return path.translate(MODEL_KEY_FOLD)


def wdt_name(directory: str) -> str:
    return "World\\Maps\\%s\\%s.wdt" % (directory, directory)


def adt_name(directory: str, x: int, y: int) -> str:
    return "World\\Maps\\%s\\%s_%d_%d.adt" % (directory, directory, x, y)


def internal_to_world(point: Vec3) -> Vec3:
    return (MAP_ORIGIN - point[0], MAP_ORIGIN - point[1], point[2])


def placement_world_position(position: Vec3) -> Vec3:
    return internal_to_world((position[2], position[0], position[1]))


def placement_rotation(degrees: Vec3) -> Matrix3:
    pitch, yaw, roll = (math.radians(angle) for angle in degrees)
    return multiply(WORLD_FLIP, multiply(rotation_z(yaw), multiply(rotation_y(pitch), rotation_x(roll))))


def placement_from_mddf(doodad: Mddf, flags: int = 0) -> Placement:
    return Placement(model=doodad.name, position=placement_world_position(doodad.position),
                     rotation=placement_rotation(doodad.rotation), scale=doodad.scale / MDDF_SCALE_ONE,
                     unique_id=doodad.unique_id, flags=flags)


def anchored_wmo_position(position: Vec3) -> Vec3:
    if position[0] == 0.0 and position[2] == 0.0:
        return (MAP_ORIGIN, position[1], MAP_ORIGIN)
    return position


def placement_from_modf(wmo: Modf, flags: int = 0) -> Placement:
    return Placement(model=wmo.name, position=placement_world_position(anchored_wmo_position(wmo.position)),
                     rotation=placement_rotation(wmo.rotation), scale=1.0, unique_id=wmo.unique_id, flags=flags)


def transform_point(placement: Placement, p: Vec3) -> Vec3:
    return add(placement.position, transform(placement.rotation, scaled(p, placement.scale)))


def placed_doodad_indices(wmo_root: WmoRoot, doodad_set: int) -> List[int]:
    chosen = [DEFAULT_DOODAD_SET]
    if doodad_set != DEFAULT_DOODAD_SET and doodad_set < len(wmo_root.doodad_sets):
        chosen.append(doodad_set)
    indices = []
    for set_index in chosen:
        if set_index >= len(wmo_root.doodad_sets):
            continue
        doodads = wmo_root.doodad_sets[set_index]
        indices.extend(range(doodads.start, min(doodads.start + doodads.count, len(wmo_root.doodads))))
    return indices


def wmo_doodad_placements(wmo_placement: Placement, wmo_root: WmoRoot,
                          doodad_set: int = DEFAULT_DOODAD_SET) -> List[Placement]:
    placements = []
    for index in placed_doodad_indices(wmo_root, doodad_set):
        doodad = wmo_root.doodads[index]
        if not doodad.name:
            continue
        placements.append(Placement(
            model=doodad.name, position=transform_point(wmo_placement, doodad.position),
            rotation=multiply(wmo_placement.rotation, quaternion_matrix(doodad.rotation)),
            scale=wmo_placement.scale * doodad.scale,
            unique_id=(wmo_placement.unique_id << WMO_DOODAD_ID_SHIFT) | index,
            flags=wmo_placement.flags | FLAG_WMO_DOODAD))
    return placements


def finite_values(values: Sequence[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def finite_lamp(lamp: Lamp) -> bool:
    return finite_values(tuple(lamp.position) + tuple(lamp.color) + (lamp.reach,))


def world_lamps(placement: Placement, verdict: ModelVerdict, map_id: int) -> List[Lamp]:
    lamps = []
    for lamp in verdict.lamps:
        lamps.append(Lamp(map_id=map_id, position=transform_point(placement, lamp.position),
                          color=scaled(lamp.color, lamp.intensity * placement.scale),
                          reach=lamp.reach * placement.scale, kind=lamp.kind, route=lamp.route,
                          flags=lamp.flags | placement.flags, model=placement.model))
    return [lamp for lamp in lamps if finite_lamp(lamp)]


def lamp_brightness(lamp: Lamp) -> float:
    return max(lamp.color)


def merge_cell(lamp: Lamp, distance: float) -> Tuple[int, int, int]:
    return tuple(math.floor(coordinate / distance) for coordinate in lamp.position)


def dedupe_lamps(lamps: Sequence[Lamp], distance: float = LAMP_MERGE_DISTANCE) -> List[Lamp]:
    order = sorted(range(len(lamps)), key=lambda index: (-lamp_brightness(lamps[index]), index))
    kept: Dict[Tuple, List[Lamp]] = {}
    survivors = []
    limit = distance * distance
    for index in order:
        lamp = lamps[index]
        cell = merge_cell(lamp, distance)
        neighbours = itertools.chain.from_iterable(
            kept.get((lamp.route, lamp.kind, cell[0] + dx, cell[1] + dy, cell[2] + dz), ())
            for dx, dy, dz in itertools.product((-1, 0, 1), repeat=3))
        if any(distance_squared(other.position, lamp.position) < limit for other in neighbours):
            continue
        kept.setdefault((lamp.route, lamp.kind) + cell, []).append(lamp)
        survivors.append(index)
    return [lamps[index] for index in sorted(survivors)]


def read_adt_prefix(chain, name: str) -> Optional[bytes]:
    prefix = chain.read_prefix(name, ADT_HEADER_SIZE)
    if not prefix:
        return None
    for _ in range(MAX_PREFIX_ROUNDS):
        needed = adt_prefix_size(prefix)
        if needed <= len(prefix):
            return prefix
        longer = chain.read_prefix(name, needed)
        if not longer or len(longer) < needed:
            raise FormatError("%s: the file ends before its placement chunks end at %d bytes" % (name, needed))
        prefix = longer
    raise FormatError("%s: the placement chunks did not settle after %d reads" % (name, MAX_PREFIX_ROUNDS))


def present_reads(chain, name: Optional[str]) -> List[VersionRead]:
    if not name:
        return []
    return [read for read in chain.version_reads(name) if read.error is not None or read.data]


def present_versions(chain, name: Optional[str]) -> List[Tuple[object, bytes]]:
    reads = present_reads(chain, name)
    for read in reads:
        if read.error is not None:
            raise read.error
    return [(read.source, read.data) for read in reads]


def readable(reads: Sequence[VersionRead]) -> List[Tuple[object, bytes]]:
    return [(read.source, read.data) for read in reads if read.error is None]


def skin_data(reads: Sequence[VersionRead]) -> List[Tuple[object, Optional[bytes]]]:
    return [(read.source, read.data) for read in reads]


def unreadable_notes(reads: Sequence[VersionRead], label: str) -> List[str]:
    return ["%sunreadable: %s" % (label, read.error) for read in reads if read.error is not None]


def stock_version(versions: Sequence[Tuple[object, bytes]]) -> Optional[Tuple[object, bytes]]:
    top_data = versions[0][1]
    for source, data in versions[1:]:
        if not source.custom and data != top_data:
            return source, data
    return None


def matching_skin(source, skins: Sequence[Tuple[object, Optional[bytes]]], top: bool) -> Optional[bytes]:
    for skin_source, data in skins:
        if skin_source.name == source.name:
            return data
    if top:
        return skins[0][1] if skins else None
    for skin_source, data in skins:
        if not skin_source.custom:
            return data
    return None


def light_count(data: bytes) -> Optional[int]:
    try:
        return m2_light_count(data)
    except FormatError:
        return None


def parsed_version(key: str, data: bytes, skin: Optional[bytes], notes: List[str], label: str) -> Optional[M2Model]:
    try:
        model = parse_m2(key, data, skin)
    except FormatError as error:
        notes.append("%sparse error: %s" % (label, error))
        return None
    notes.extend(label + note for note in model.notes)
    return model


def unevaluated(key: str, note: str) -> Tuple[ModelVerdict, ModelCensus]:
    return ModelVerdict(route=None, notes=[note]), ModelCensus(key, notes=[note])


def skin_versions(chain, key: str, notes: List[str]) -> List[Tuple[object, Optional[bytes]]]:
    try:
        reads = present_reads(chain, skin_path(key))
    except MpqError as error:
        notes.append("%sunreadable: %s" % (SKIN_LABEL, error))
        return []
    notes.extend(unreadable_notes(reads, SKIN_LABEL))
    return skin_data(reads)


def version_light_count(read: VersionRead) -> Optional[int]:
    return None if read.error is not None else light_count(read.data)


def evaluate_model(chain, key: str, classify: Classify) -> Tuple[ModelVerdict, ModelCensus]:
    try:
        reads = present_reads(chain, key)
    except MpqError as error:
        return unevaluated(key, "unreadable: %s" % error)
    if not reads:
        return unevaluated(key, NOTE_MISSING_FILE)
    if reads[0].error is not None:
        return unevaluated(key, "unreadable: %s" % reads[0].error)
    notes = unreadable_notes(reads[1:], LOWER_VERSION_LABEL)
    versions = readable(reads)
    skins = skin_versions(chain, key, notes)
    top_source, top_data = versions[0]
    top = parsed_version(key, top_data, matching_skin(top_source, skins, True), notes, "")
    stock = stock_version(versions)
    stock_model = None
    if top is not None and stock is not None:
        stock_model = parsed_version(key, stock[1], matching_skin(stock[0], skins, False), notes, "stock: ")
    verdict = ModelVerdict(route=None) if top is None else classify(top, stock_model)
    verdict.notes.extend(note for note in notes if note not in verdict.notes)
    census = ModelCensus(key, archives=[read.source.name for read in reads],
                         version_lights=[version_light_count(read) for read in reads],
                         top_lights=len(top.lights) if top else 0,
                         stock_lights=len(stock_model.lights) if stock_model else 0,
                         route=verdict.route, notes=list(verdict.notes))
    return verdict, census


def default_classify() -> Classify:
    from lamp_rules import classify
    return classify


class MapWalk:
    def __init__(self, chain, map_id: int, directory: str, model_cache: Dict[str, ModelVerdict], census: Census,
                 classify: Classify, wmo_cache: Dict[str, Optional[WmoRoot]]):
        self.chain = chain
        self.map_id = map_id
        self.directory = directory
        self.model_cache = model_cache
        self.census = census
        self.record = census.map(map_id, directory)
        self.classify = classify
        self.wmo_cache = wmo_cache
        self.placed = set()
        self.missing_models = set()
        self.lamps: List[Lamp] = []

    def run(self) -> List[Lamp]:
        try:
            data = self.chain.read(wdt_name(self.directory))
            wdt = parse_wdt(data) if data else None
        except READ_ERRORS:
            count(self.record.errors, FILE_WDT)
            return []
        if wdt is None:
            count(self.record.missing, FILE_WDT)
            return []
        self.record.tiles += len(wdt.tiles)
        for x, y in wdt.tiles:
            self.walk_tile(x, y)
        if wdt.global_wmo_placement is not None:
            self.place_wmo(wdt.global_wmo_placement, FLAG_GLOBAL_WMO)
        lamps = dedupe_lamps(self.lamps)
        self.record.lamps += len(lamps)
        for lamp in lamps:
            count(self.record.routes, lamp.route)
        return lamps

    def first_placement(self, kind: str, unique_id: int) -> bool:
        key = (kind, unique_id)
        if key in self.placed:
            return False
        self.placed.add(key)
        return True

    def walk_tile(self, x: int, y: int) -> None:
        name = adt_name(self.directory, x, y)
        try:
            prefix = read_adt_prefix(self.chain, name)
            adt = parse_adt(prefix) if prefix else None
        except READ_ERRORS:
            count(self.record.errors, FILE_ADT)
            return
        if adt is None:
            count(self.record.missing, FILE_ADT)
            return
        for doodad in adt.doodads:
            if self.first_placement(PLACEMENT_M2, doodad.unique_id) and self.finite_record(doodad):
                self.place_model(placement_from_mddf(doodad))
        for wmo in adt.wmos:
            if self.first_placement(PLACEMENT_WMO, wmo.unique_id):
                self.place_wmo(wmo, 0)

    def finite_record(self, record) -> bool:
        if finite_values(tuple(record.position) + tuple(record.rotation)):
            return True
        count(self.record.errors, NOT_FINITE)
        return False

    def place_wmo(self, wmo: Modf, flags: int) -> None:
        if not wmo.name:
            count(self.record.errors, NAMELESS)
            return
        if not self.finite_record(wmo):
            return
        self.record.wmo_placements += 1
        root = self.wmo_root(wmo.name)
        if root is None:
            return
        for placement in wmo_doodad_placements(placement_from_modf(wmo, flags), root, wmo.doodad_set):
            self.place_model(placement)

    def wmo_root(self, name: str) -> Optional[WmoRoot]:
        key = model_key(name)
        if key not in self.wmo_cache:
            self.wmo_cache[key] = self.read_wmo_root(key)
        return self.wmo_cache[key]

    def read_wmo_root(self, key: str) -> Optional[WmoRoot]:
        try:
            data = self.chain.read(key)
            root = parse_wmo_root(data, key) if data else None
        except READ_ERRORS:
            count(self.record.errors, FILE_WMO)
            return None
        if root is None:
            count(self.record.missing, FILE_WMO)
        return root

    def place_model(self, placement: Placement) -> None:
        if not placement.model:
            count(self.record.errors, NAMELESS)
            return
        self.record.placements += 1
        key = model_key(placement.model)
        verdict = self.verdict(key)
        if NOTE_MISSING_FILE in verdict.notes and key not in self.missing_models:
            self.missing_models.add(key)
            count(self.record.missing, FILE_M2)
        count(self.census.models[key].placements, self.map_id)
        self.lamps.extend(world_lamps(placement, verdict, self.map_id))

    def verdict(self, key: str) -> ModelVerdict:
        if key not in self.model_cache:
            verdict, model = evaluate_model(self.chain, key, self.classify)
            self.model_cache[key] = verdict
            self.census.models[key] = model
        verdict = self.model_cache[key]
        if key not in self.census.models:
            self.census.models[key] = ModelCensus(key, route=verdict.route, notes=list(verdict.notes))
        return verdict


def walk_map(chain, map_id: int, directory: str, model_cache: Dict[str, ModelVerdict],
             census: Optional[Census] = None, classify: Optional[Classify] = None,
             wmo_cache: Optional[Dict[str, Optional[WmoRoot]]] = None) -> List[Lamp]:
    walk = MapWalk(chain, map_id, directory, model_cache, Census() if census is None else census,
                   classify or default_classify(), {} if wmo_cache is None else wmo_cache)
    return walk.run()
