import itertools
import math
import os
import struct
from dataclasses import dataclass, field, replace
from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

from lamp_types import KIND_CHANDELIER, KIND_UNKNOWN, ROUTE_AUTHORED, ROUTE_EMISSIVE, ArchiveSource, Lamp, Vec3

HEADER = struct.Struct("<4s7I")
SOURCE = struct.Struct("<64sQ")
MAP = struct.Struct("<5I")
CELL = struct.Struct("<2H2I")
LAMP = struct.Struct("<3f3ffHBB")
FLOAT32 = struct.Struct("<f")

MAGIC = b"LXLD"
VERSION = 1
RESERVED = (0, 0)
MAX_SOURCES = 1024
SOURCE_PATH_LIMIT = 63
SOURCE_SEPARATOR = "\\"
SOURCE_ENCODING = "ascii"
MAX_SOURCE_SIZE = 0xFFFFFFFFFFFFFFFF
MAX_U32 = 0xFFFFFFFF
MAX_FLAGS = 0xFFFF

GRID_ORIGIN = 17066.666
CELL_YARDS = 133.33333
CELLS_PER_SIDE = 256
MAX_HORIZONTAL = 17068.0
MAX_HEIGHT = 20000.0
MAX_REACH = 200.0
MAX_COLOR = 64.0
KINDS = range(KIND_UNKNOWN, KIND_CHANDELIER + 1)
ROUTES = range(ROUTE_AUTHORED, ROUTE_EMISSIVE + 1)
TEMPORARY_SUFFIX = ".part"


class LampDataError(ValueError):
    pass


class SourceRecord(NamedTuple):
    path: str
    size: int


class MapRecord(NamedTuple):
    map_id: int
    first_cell: int
    cell_count: int
    first_lamp: int
    lamp_count: int


class CellRecord(NamedTuple):
    x: int
    y: int
    first_lamp: int
    lamp_count: int


@dataclass
class LampData:
    sources: List[SourceRecord]
    maps: List[MapRecord]
    cells: List[CellRecord]
    lamps: List[Lamp]

    def map_lamps(self, map_id: int) -> List[Lamp]:
        return [lamp for lamp in self.lamps if lamp.map_id == map_id]


@dataclass
class PreparedLamps:
    lamps: List[Lamp] = field(default_factory=list)
    clamped: int = 0
    dropped: int = 0


def float32(value: float) -> float:
    try:
        return FLOAT32.unpack(FLOAT32.pack(value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def cell_of(coordinate: float) -> int:
    cell = math.floor((coordinate + GRID_ORIGIN) / CELL_YARDS)
    return min(max(cell, 0), CELLS_PER_SIDE - 1)


def cell_key(lamp: Lamp) -> Tuple[int, int]:
    return cell_of(lamp.position[0]), cell_of(lamp.position[1])


def stored_vector(values: Sequence[float]) -> Vec3:
    return tuple(float32(value) for value in values)


def stored_lamp(lamp: Lamp) -> Lamp:
    return replace(lamp, position=stored_vector(lamp.position), color=stored_vector(lamp.color),
                   reach=float32(lamp.reach))


def finite(values: Iterable[float]) -> bool:
    return all(math.isfinite(value) for value in values)


def inside_world(position: Vec3) -> bool:
    return abs(position[0]) <= MAX_HORIZONTAL and abs(position[1]) <= MAX_HORIZONTAL and abs(position[2]) <= MAX_HEIGHT


def whole_number_in(value, allowed: range) -> bool:
    return isinstance(value, int) and value in allowed


def lamp_problem(lamp: Lamp) -> Optional[str]:
    if len(lamp.position) != 3 or len(lamp.color) != 3:
        return "needs three position and three colour components"
    if not finite(tuple(lamp.position) + tuple(lamp.color) + (lamp.reach,)):
        return "is not finite"
    if not inside_world(lamp.position):
        return "lies beyond the world's edge, or higher or lower than %g yd" % MAX_HEIGHT
    if not 0.0 < lamp.reach <= MAX_REACH:
        return "reaches %g yd, outside (0, %g]" % (lamp.reach, MAX_REACH)
    if not all(0.0 <= channel <= MAX_COLOR for channel in lamp.color):
        return "has a colour outside [0, %g]" % MAX_COLOR
    if not whole_number_in(lamp.kind, KINDS):
        return "has the unknown kind %r" % (lamp.kind,)
    if not whole_number_in(lamp.route, ROUTES):
        return "has the unknown route %r" % (lamp.route,)
    if not whole_number_in(lamp.flags, range(MAX_FLAGS + 1)):
        return "has flags %r beyond 16 bits" % (lamp.flags,)
    if not whole_number_in(lamp.map_id, range(MAX_U32 + 1)):
        return "is on map %r, which is no 32-bit map id" % (lamp.map_id,)
    return None


def lamp_label(lamp: Lamp) -> str:
    return "the lamp on map %s at (%s)%s" % (lamp.map_id, ", ".join("%g" % value for value in lamp.position),
                                            " of " + lamp.model if lamp.model else "")


def checked_lamp(lamp: Lamp) -> Lamp:
    stored = stored_lamp(lamp)
    problem = lamp_problem(stored)
    if problem is not None:
        raise LampDataError("%s %s" % (lamp_label(lamp), problem))
    return stored


def lamp_order(lamp: Lamp) -> tuple:
    x, y = cell_key(lamp)
    return (lamp.map_id, x * CELLS_PER_SIDE + y, tuple(lamp.position), lamp.route, lamp.kind, lamp.flags,
            tuple(lamp.color), lamp.reach, lamp.model)


def index_lamps(lamps: Sequence[Lamp]) -> Tuple[List[MapRecord], List[CellRecord]]:
    maps: List[MapRecord] = []
    cells: List[CellRecord] = []
    for map_id, members in itertools.groupby(range(len(lamps)), key=lambda index: lamps[index].map_id):
        on_map = list(members)
        first_cell = len(cells)
        for (x, y), in_cell in itertools.groupby(on_map, key=lambda index: cell_key(lamps[index])):
            indices = list(in_cell)
            cells.append(CellRecord(x, y, indices[0], len(indices)))
        maps.append(MapRecord(map_id, first_cell, len(cells) - first_cell, on_map[0], len(on_map)))
    return maps, cells


def stored_source_path(name: str) -> bytes:
    return name.replace("/", SOURCE_SEPARATOR).encode(SOURCE_ENCODING, "replace")[:SOURCE_PATH_LIMIT]


def source_bytes(source: ArchiveSource) -> bytes:
    if not 0 <= source.size <= MAX_SOURCE_SIZE:
        raise LampDataError("archive %s has the size %r, which no 64-bit count holds" % (source.name, source.size))
    return SOURCE.pack(stored_source_path(source.name), source.size)


def lamp_bytes(lamp: Lamp) -> bytes:
    return LAMP.pack(*lamp.position, *lamp.color, lamp.reach, lamp.flags, lamp.kind, lamp.route)


def lamp_data_bytes(lamps: Iterable[Lamp], sources: Sequence[ArchiveSource] = ()) -> bytes:
    if len(sources) > MAX_SOURCES:
        raise LampDataError("%d source archives, more than the %d lampdata.bin can name" % (len(sources), MAX_SOURCES))
    ordered = sorted((checked_lamp(lamp) for lamp in lamps), key=lamp_order)
    maps, cells = index_lamps(ordered)
    parts = [HEADER.pack(MAGIC, VERSION, len(maps), len(cells), len(ordered), len(sources), *RESERVED)]
    parts.extend(source_bytes(source) for source in sources)
    parts.extend(MAP.pack(*record) for record in maps)
    parts.extend(CELL.pack(*record) for record in cells)
    parts.extend(lamp_bytes(lamp) for lamp in ordered)
    data = b"".join(parts)
    read_lamp_data(data)
    return data


def write_lamp_data(path: str, lamps: Iterable[Lamp], sources: Sequence[ArchiveSource] = ()) -> bytes:
    data = lamp_data_bytes(lamps, sources)
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    temporary = path + TEMPORARY_SUFFIX
    with open(temporary, "wb") as handle:
        handle.write(data)
    os.replace(temporary, path)
    return data


def expected_size(map_count: int, cell_count: int, lamp_count: int, source_count: int) -> int:
    return (HEADER.size + source_count * SOURCE.size + map_count * MAP.size + cell_count * CELL.size
            + lamp_count * LAMP.size)


def records(data: bytes, offset: int, layout: struct.Struct, count: int) -> Tuple[List[tuple], int]:
    values = [layout.unpack_from(data, offset + index * layout.size) for index in range(count)]
    return values, offset + count * layout.size


def source_record(values: tuple) -> SourceRecord:
    raw, size = values
    return SourceRecord(raw.split(b"\0", 1)[0].decode(SOURCE_ENCODING, "replace"), size)


def maps_contiguous(maps: Sequence[MapRecord], cell_count: int, lamp_count: int) -> bool:
    cells = 0
    lamps = 0
    for index, record in enumerate(maps):
        in_order = index == 0 or record.map_id > maps[index - 1].map_id
        if not in_order or record.first_cell != cells or record.first_lamp != lamps:
            return False
        cells += record.cell_count
        lamps += record.lamp_count
    return cells == cell_count and lamps == lamp_count


def cells_contiguous(record: MapRecord, cells: Sequence[CellRecord]) -> bool:
    next_lamp = record.first_lamp
    previous_key = -1
    for cell in cells[record.first_cell:record.first_cell + record.cell_count]:
        key = cell.x * CELLS_PER_SIDE + cell.y
        on_grid = cell.x < CELLS_PER_SIDE and cell.y < CELLS_PER_SIDE
        if not on_grid or key <= previous_key or cell.lamp_count == 0 or cell.first_lamp != next_lamp:
            return False
        previous_key = key
        next_lamp += cell.lamp_count
    return next_lamp == record.first_lamp + record.lamp_count


def read_lamp(values: tuple, map_id: int) -> Lamp:
    return Lamp(map_id=map_id, position=values[0:3], color=values[3:6], reach=values[6], flags=values[7],
                kind=values[8], route=values[9])


def checked_cell_lamps(cell: CellRecord, lamps: Sequence[Lamp]) -> None:
    for lamp in lamps[cell.first_lamp:cell.first_lamp + cell.lamp_count]:
        problem = lamp_problem(lamp)
        if problem is not None:
            raise LampDataError("%s %s" % (lamp_label(lamp), problem))
        if cell_key(lamp) != (cell.x, cell.y):
            raise LampDataError("%s lies outside its cell %d, %d" % (lamp_label(lamp), cell.x, cell.y))


def read_lamp_data(data: bytes) -> LampData:
    if len(data) < HEADER.size:
        raise LampDataError("shorter than its header")
    magic, version, map_count, cell_count, lamp_count, source_count = HEADER.unpack_from(data, 0)[:6]
    if magic != MAGIC:
        raise LampDataError("not a lamp data file")
    if version != VERSION:
        raise LampDataError("format version %d instead of %d" % (version, VERSION))
    if source_count > MAX_SOURCES:
        raise LampDataError("more than %d source archives" % MAX_SOURCES)
    if expected_size(map_count, cell_count, lamp_count, source_count) != len(data):
        raise LampDataError("truncated or padded")
    raw_sources, offset = records(data, HEADER.size, SOURCE, source_count)
    raw_maps, offset = records(data, offset, MAP, map_count)
    raw_cells, offset = records(data, offset, CELL, cell_count)
    raw_lamps, offset = records(data, offset, LAMP, lamp_count)
    maps = [MapRecord(*values) for values in raw_maps]
    cells = [CellRecord(*values) for values in raw_cells]
    if not maps_contiguous(maps, cell_count, lamp_count):
        raise LampDataError("maps out of order, or their cell and lamp ranges do not follow each other")
    lamps: List[Lamp] = []
    for record in maps:
        if not cells_contiguous(record, cells):
            raise LampDataError("the cells of map %d are out of order, empty or do not cover its lamps"
                                % record.map_id)
        lamps.extend(read_lamp(values, record.map_id)
                     for values in raw_lamps[record.first_lamp:record.first_lamp + record.lamp_count])
    for cell in cells:
        checked_cell_lamps(cell, lamps)
    return LampData(sources=[source_record(values) for values in raw_sources], maps=maps, cells=cells, lamps=lamps)


def read_lamp_data_file(path: str) -> LampData:
    with open(path, "rb") as handle:
        return read_lamp_data(handle.read())


def bounded_color(color: Vec3) -> Vec3:
    positive = tuple(max(channel, 0.0) for channel in color)
    peak = max(positive)
    if peak <= MAX_COLOR:
        return positive
    return tuple(min(channel * (MAX_COLOR / peak), MAX_COLOR) for channel in positive)


def storable_lamp(lamp: Lamp) -> Tuple[Optional[Lamp], bool]:
    values = tuple(lamp.position) + tuple(lamp.color) + (lamp.reach,)
    if not finite(values) or not lamp.reach > 0.0 or not inside_world(stored_vector(lamp.position)):
        return None, False
    color = bounded_color(lamp.color)
    reach = min(lamp.reach, MAX_REACH)
    clamped = color != tuple(lamp.color) or reach != lamp.reach
    stored = stored_lamp(replace(lamp, color=color, reach=reach))
    if not stored.reach > 0.0:
        return None, False
    return replace(lamp, color=color, reach=reach), clamped


def prepare_lamps(lamps: Iterable[Lamp]) -> PreparedLamps:
    prepared = PreparedLamps()
    for lamp in lamps:
        kept, clamped = storable_lamp(lamp)
        if kept is None:
            prepared.dropped += 1
            continue
        prepared.lamps.append(kept)
        prepared.clamped += int(clamped)
    return prepared
