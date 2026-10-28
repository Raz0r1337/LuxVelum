import math
import ntpath
import struct
from dataclasses import dataclass, field, replace
from typing import Dict, Iterator, List, NamedTuple, Optional, Sequence, Tuple

from lamp_math import (IDENTITY_AFFINE, IDENTITY_QUATERNION, ORIGIN, UNIT_SCALE, Affine, Quaternion,
                       apply_affine, compose_affine, pivoted_affine)
from lamp_types import M2Batch, M2Emitter, M2Light, M2Model, Vec3


class FormatError(ValueError):
    pass


U8 = struct.Struct("<B")
U16 = struct.Struct("<H")
I16 = struct.Struct("<h")
U32 = struct.Struct("<I")
F32 = struct.Struct("<f")
VEC2 = struct.Struct("<2f")
VEC3 = struct.Struct("<3f")
COMPRESSED_QUATERNION = struct.Struct("<4h")
M2_ARRAY = struct.Struct("<2I")
CHUNK_HEADER = struct.Struct("<4sI")

WDBC_MAGIC = b"WDBC"
WDBC_HEADER = struct.Struct("<4s4I")
MAP_RECORD_PREFIX = struct.Struct("<2I")

MVER = b"MVER"
MPHD = b"MPHD"
MAIN = b"MAIN"
MHDR = b"MHDR"
MMDX = b"MMDX"
MMID = b"MMID"
MWMO = b"MWMO"
MWID = b"MWID"
MDDF = b"MDDF"
MODF = b"MODF"
MOHD = b"MOHD"
MODS = b"MODS"
MODN = b"MODN"
MODD = b"MODD"

WDT_GRID = 64
MAIN_ENTRY_SIZE = 8
MAIN_SIZE = WDT_GRID * WDT_GRID * MAIN_ENTRY_SIZE
ADT_PRESENT = 0x1
MPHD_GLOBAL_WMO = 0x1

MVER_CHUNK_SIZE = CHUNK_HEADER.size + U32.size
MHDR_DATA_START = MVER_CHUNK_SIZE + CHUNK_HEADER.size
MHDR_DATA_SIZE = 64
ADT_HEADER_SIZE = MHDR_DATA_START + MHDR_DATA_SIZE
MHDR_OFFSETS = struct.Struct("<9I")
MHDR_PLACEMENT_FIELDS = ((MMDX, 3), (MMID, 4), (MWMO, 5), (MWID, 6), (MDDF, 7), (MODF, 8))

MDDF_RECORD = struct.Struct("<2I3f3fHH")
MODF_RECORD = struct.Struct("<2I3f3f3f3fHHHH")
MODS_RECORD = struct.Struct("<20s3I")
MODD_RECORD = struct.Struct("<I3f4ffI")
MODD_NAME_MASK = 0xFFFFFF
LEGACY_MODEL_SUFFIXES = (".mdx", ".mdl")
MODEL_SUFFIX = ".m2"

M2_MAGIC = b"MD20"
M2_PREAMBLE = struct.Struct("<4sI")
WOTLK_VERSION = 264
CATA_VERSION = 272

M2_SEQUENCE_SIZE = 64
SEQUENCE_FLAGS = 12
SEQUENCE_INLINE = 0x20

M2_TRACK_SIZE = 20
TRACK_HEAD = struct.Struct("<Hh")
TRACK_VALUES = 12
FAKE_TRACK_VALUES = 8

M2_BONE_SIZE = 88
BONE_PARENT = 8
BONE_TRANSLATION = 16
BONE_ROTATION = BONE_TRANSLATION + M2_TRACK_SIZE
BONE_SCALE = BONE_ROTATION + M2_TRACK_SIZE
BONE_PIVOT = BONE_SCALE + M2_TRACK_SIZE

M2_TEXTURE = struct.Struct("<2I2I")
TEXTURE_FILE = 0
M2_MATERIAL = struct.Struct("<2H")
MATERIAL_UNLIT = 0x1

M2_LIGHT_SIZE = 156
LIGHT_HEAD = struct.Struct("<Hh3f")
LIGHT_DIFFUSE_COLOR = 56
LIGHT_DIFFUSE_INTENSITY = LIGHT_DIFFUSE_COLOR + M2_TRACK_SIZE
LIGHT_ATTENUATION_START = LIGHT_DIFFUSE_INTENSITY + M2_TRACK_SIZE
LIGHT_ATTENUATION_END = LIGHT_ATTENUATION_START + M2_TRACK_SIZE
LIGHT_VISIBILITY = LIGHT_ATTENUATION_END + M2_TRACK_SIZE

M2_PARTICLE_SIZE = 476
CATA_PARTICLE_SIZE = 492
EMITTER_HEAD = struct.Struct("<2I3f2H")
EMITTER_BLEND = 40
EMITTER_EMISSION_RATE = 176
EMITTER_COLOR = 260
EMITTER_ALPHA = 276
EMITTER_SCALE = 292
COLOR_CHANNEL_MAX = 255.0
FIXED16_ONE = 32767.0
COMPRESSED_QUATERNION_SHIFT = 32768

SKIN_MAGIC = b"SKIN"
SKIN_SUBMESHES = 28
SKIN_BATCHES = 36
SKIN_SUBMESH_SIZE = 48
SUBMESH_INDEX_COUNT = 10
SUBMESH_CENTER = 20
SKIN_BATCH_SIZE = 24
SKIN_BATCH = struct.Struct("<BbHHHhHHHH")


@dataclass(frozen=True)
class HeaderLayout:
    sequences: Optional[int]
    bones: Optional[int]
    textures: int
    materials: Optional[int]
    texture_lookup: Optional[int]
    bounds_min: int
    bounds_max: int
    lights: Optional[int]
    emitters: Optional[int]
    emitter_size: int


WOTLK_LAYOUT = HeaderLayout(sequences=0x1C, bones=0x2C, textures=0x50, materials=0x70, texture_lookup=0x80,
                            bounds_min=0xA0, bounds_max=0xAC, lights=0x108, emitters=0x128,
                            emitter_size=M2_PARTICLE_SIZE)
CATA_LAYOUT = replace(WOTLK_LAYOUT, emitter_size=CATA_PARTICLE_SIZE)
LEGACY_LAYOUT = HeaderLayout(sequences=None, bones=None, textures=0x5C, materials=None, texture_lookup=None,
                             bounds_min=0xB4, bounds_max=0xC0, lights=None, emitters=None, emitter_size=0)
LEGACY_LIGHT_COUNT = 0x11C


@dataclass
class Mddf:
    name_id: int
    unique_id: int
    position: Vec3
    rotation: Vec3
    scale: int
    flags: int
    name: str = ""


@dataclass
class Modf:
    name_id: int
    unique_id: int
    position: Vec3
    rotation: Vec3
    extents_min: Vec3
    extents_max: Vec3
    flags: int
    doodad_set: int
    name_set: int
    name: str = ""


@dataclass
class Wdt:
    tiles: List[Tuple[int, int]]
    global_wmo: Optional[str]
    global_wmo_placement: Optional[Modf]


@dataclass
class Adt:
    m2_names: List[str]
    wmo_names: List[str]
    doodads: List[Mddf]
    wmos: List[Modf]


class DoodadSet(NamedTuple):
    name: str
    start: int
    count: int


class WmoDoodad(NamedTuple):
    name: str
    position: Vec3
    rotation: Quaternion
    scale: float


@dataclass
class WmoRoot:
    doodad_sets: List[DoodadSet]
    doodads: List[WmoDoodad]


@dataclass
class ParsedM2Model(M2Model):
    notes: List[str] = field(default_factory=list)


class BinaryView:
    def __init__(self, data: bytes, label: str):
        self.data = data
        self.label = label

    def contains(self, offset: int, size: int) -> bool:
        return offset >= 0 and size >= 0 and offset + size <= len(self.data)

    def require(self, offset: int, size: int, what: str) -> None:
        if not self.contains(offset, size):
            raise FormatError("%s: %s (%d bytes at 0x%X) lies outside the file (%d bytes)"
                              % (self.label, what, size, offset, len(self.data)))

    def unpack(self, layout: struct.Struct, offset: int, what: str) -> tuple:
        self.require(offset, layout.size, what)
        return layout.unpack_from(self.data, offset)

    def elements(self, offset: int, stride: int, what: str) -> range:
        count, start = self.unpack(M2_ARRAY, offset, what + " header")
        if count == 0:
            return range(0)
        self.require(start, count * stride, what)
        return range(start, start + count * stride, stride)


def decoded(raw: bytes) -> str:
    return raw.decode("latin-1")


def string_at(block: bytes, offset: int) -> Optional[str]:
    if offset < 0 or offset >= len(block):
        return None
    end = block.find(b"\0", offset)
    return decoded(block[offset:] if end < 0 else block[offset:end])


def string_list(block: bytes) -> List[str]:
    parts = block.split(b"\0")
    if parts and not parts[-1]:
        parts.pop()
    return [decoded(part) for part in parts]


def model_file_name(name: str) -> str:
    root, suffix = ntpath.splitext(name)
    return root + MODEL_SUFFIX if suffix.lower() in LEGACY_MODEL_SUFFIXES else name


def chunks(view: BinaryView) -> Iterator[Tuple[bytes, int, int]]:
    offset = 0
    while offset + CHUNK_HEADER.size <= len(view.data):
        stored, size = CHUNK_HEADER.unpack_from(view.data, offset)
        start = offset + CHUNK_HEADER.size
        magic = stored[::-1]
        view.require(start, size, "chunk " + decoded(magic))
        yield magic, start, size
        offset = start + size


def first_chunks(view: BinaryView) -> Dict[bytes, Tuple[int, int]]:
    found: Dict[bytes, Tuple[int, int]] = {}
    for magic, start, size in chunks(view):
        found.setdefault(magic, (start, size))
    return found


def chunk_bytes(view: BinaryView, found: Dict[bytes, Tuple[int, int]], magic: bytes) -> bytes:
    if magic not in found:
        return b""
    start, size = found[magic]
    return view.data[start:start + size]


def parse_map_dbc(data: bytes) -> List[Tuple[int, str]]:
    view = BinaryView(data, "Map.dbc")
    magic, records, _, record_size, string_size = view.unpack(WDBC_HEADER, 0, "header")
    if magic != WDBC_MAGIC:
        raise FormatError("Map.dbc: magic %r is not WDBC" % magic)
    if records and record_size < MAP_RECORD_PREFIX.size:
        raise FormatError("Map.dbc: records of %d bytes cannot hold an id and a directory" % record_size)
    strings_start = WDBC_HEADER.size + records * record_size
    view.require(strings_start, string_size, "string block")
    strings = data[strings_start:strings_start + string_size]
    maps = []
    for index in range(records):
        map_id, directory_offset = MAP_RECORD_PREFIX.unpack_from(data, WDBC_HEADER.size + index * record_size)
        directory = string_at(strings, directory_offset)
        if directory is None:
            raise FormatError("Map.dbc: map %d names directory offset %d outside the string block"
                              % (map_id, directory_offset))
        maps.append((map_id, directory))
    return maps


def read_modf(data: bytes, offset: int, names: Sequence[str]) -> Modf:
    values = MODF_RECORD.unpack_from(data, offset)
    name_id = values[0]
    return Modf(name_id=name_id, unique_id=values[1], position=values[2:5], rotation=values[5:8],
                extents_min=values[8:11], extents_max=values[11:14], flags=values[14], doodad_set=values[15],
                name_set=values[16], name=names[name_id] if name_id < len(names) else "")


def read_mddf(data: bytes, offset: int, names: Sequence[str]) -> Mddf:
    values = MDDF_RECORD.unpack_from(data, offset)
    name_id = values[0]
    return Mddf(name_id=name_id, unique_id=values[1], position=values[2:5], rotation=values[5:8], scale=values[8],
                flags=values[9], name=names[name_id] if name_id < len(names) else "")


def records(block: bytes, layout: struct.Struct) -> range:
    return range(0, len(block) - len(block) % layout.size, layout.size)


def parse_wdt(data: bytes) -> Wdt:
    view = BinaryView(data, "WDT")
    found = first_chunks(view)
    mphd = chunk_bytes(view, found, MPHD)
    flags = U32.unpack_from(mphd, 0)[0] if len(mphd) >= U32.size else 0
    main = chunk_bytes(view, found, MAIN)
    if main and len(main) < MAIN_SIZE:
        raise FormatError("WDT: MAIN holds %d bytes instead of %d" % (len(main), MAIN_SIZE))
    tiles = []
    if main:
        for y in range(WDT_GRID):
            for x in range(WDT_GRID):
                if U32.unpack_from(main, (y * WDT_GRID + x) * MAIN_ENTRY_SIZE)[0] & ADT_PRESENT:
                    tiles.append((x, y))
    names = string_list(chunk_bytes(view, found, MWMO))
    placements = chunk_bytes(view, found, MODF)
    placement = None
    if flags & MPHD_GLOBAL_WMO and len(placements) >= MODF_RECORD.size:
        placement = read_modf(placements, 0, names)
    if placement is None or not placement.name:
        return Wdt(tiles=tiles, global_wmo=None, global_wmo_placement=None)
    return Wdt(tiles=tiles, global_wmo=placement.name, global_wmo_placement=placement)


def mhdr_chunk_offsets(view: BinaryView) -> Dict[bytes, int]:
    if len(view.data) < ADT_HEADER_SIZE:
        raise FormatError("%s: %d bytes cannot hold MVER and MHDR" % (view.label, len(view.data)))
    if CHUNK_HEADER.unpack_from(view.data, 0)[0][::-1] != MVER:
        raise FormatError("%s: the file does not start with MVER" % view.label)
    if CHUNK_HEADER.unpack_from(view.data, MVER_CHUNK_SIZE)[0][::-1] != MHDR:
        raise FormatError("%s: MHDR does not follow MVER" % view.label)
    offsets = MHDR_OFFSETS.unpack_from(view.data, MHDR_DATA_START)
    return {magic: MHDR_DATA_START + offsets[index] for magic, index in MHDR_PLACEMENT_FIELDS if offsets[index]}


def placement_chunk_size(view: BinaryView, magic: bytes, offset: int) -> int:
    stored, size = view.unpack(CHUNK_HEADER, offset, "chunk header of " + decoded(magic))
    if stored[::-1] != magic:
        raise FormatError("%s: MHDR points %s at 0x%X, which holds %s"
                          % (view.label, decoded(magic), offset, decoded(stored[::-1])))
    return size


def adt_prefix_size(prefix: bytes) -> int:
    view = BinaryView(prefix, "ADT")
    needed = ADT_HEADER_SIZE
    for magic, offset in mhdr_chunk_offsets(view).items():
        header_end = offset + CHUNK_HEADER.size
        if header_end > len(prefix):
            needed = max(needed, header_end)
        else:
            needed = max(needed, header_end + placement_chunk_size(view, magic, offset))
    return needed


def adt_chunk(view: BinaryView, offsets: Dict[bytes, int], magic: bytes) -> bytes:
    if magic not in offsets:
        return b""
    start = offsets[magic] + CHUNK_HEADER.size
    size = placement_chunk_size(view, magic, offsets[magic])
    view.require(start, size, decoded(magic))
    return view.data[start:start + size]


def resolved_names(block: bytes, offsets_block: bytes) -> List[str]:
    names = []
    for offset in records(offsets_block, U32):
        name = string_at(block, U32.unpack_from(offsets_block, offset)[0])
        names.append(model_file_name(name) if name else "")
    return names


def parse_adt(prefix: bytes) -> Adt:
    view = BinaryView(prefix, "ADT")
    offsets = mhdr_chunk_offsets(view)
    m2_names = resolved_names(adt_chunk(view, offsets, MMDX), adt_chunk(view, offsets, MMID))
    wmo_names = resolved_names(adt_chunk(view, offsets, MWMO), adt_chunk(view, offsets, MWID))
    doodad_block = adt_chunk(view, offsets, MDDF)
    wmo_block = adt_chunk(view, offsets, MODF)
    doodads = [read_mddf(doodad_block, offset, m2_names) for offset in records(doodad_block, MDDF_RECORD)]
    wmos = [read_modf(wmo_block, offset, wmo_names) for offset in records(wmo_block, MODF_RECORD)]
    return Adt(m2_names=m2_names, wmo_names=wmo_names, doodads=doodads, wmos=wmos)


def parse_wmo_root(data: bytes, label: str = "WMO") -> WmoRoot:
    view = BinaryView(data, label)
    found = first_chunks(view)
    if MOHD not in found:
        raise FormatError("%s: no MOHD chunk, so this is not a WMO root" % label)
    set_block = chunk_bytes(view, found, MODS)
    names = chunk_bytes(view, found, MODN)
    doodad_block = chunk_bytes(view, found, MODD)
    doodad_sets = []
    for offset in records(set_block, MODS_RECORD):
        raw_name, start, count, _ = MODS_RECORD.unpack_from(set_block, offset)
        doodad_sets.append(DoodadSet(decoded(raw_name.split(b"\0", 1)[0]), start, count))
    doodads = []
    for offset in records(doodad_block, MODD_RECORD):
        values = MODD_RECORD.unpack_from(doodad_block, offset)
        name = string_at(names, values[0] & MODD_NAME_MASK)
        doodads.append(WmoDoodad(model_file_name(name) if name else "", values[1:4], values[4:8], values[8]))
    return WmoRoot(doodad_sets=doodad_sets, doodads=doodads)


def header_layout(version: int) -> Tuple[HeaderLayout, List[str]]:
    if version == WOTLK_VERSION:
        return WOTLK_LAYOUT, []
    if version < WOTLK_VERSION:
        return LEGACY_LAYOUT, ["version %d: pre-WotLK layout, only bounds and textures read" % version]
    if version >= CATA_VERSION:
        return CATA_LAYOUT, ["version %d: read with the WotLK layout and %d-byte emitters"
                             % (version, CATA_PARTICLE_SIZE)]
    return WOTLK_LAYOUT, ["version %d: read with the WotLK layout" % version]


def decompressed_component(value: int) -> float:
    return (value + COMPRESSED_QUATERNION_SHIFT if value < 0 else value - FIXED16_ONE) / FIXED16_ONE


def decompressed_quaternion(values: Sequence[int]) -> Quaternion:
    return tuple(decompressed_component(value) for value in values)


class TrackReader:
    def __init__(self, view: BinaryView, first_sequence_inline: bool):
        self.view = view
        self.first_sequence_inline = first_sequence_inline

    def first_keys(self, offset: int, layout: struct.Struct) -> range:
        _, global_sequence = self.view.unpack(TRACK_HEAD, offset, "track")
        sub_arrays = self.view.elements(offset + TRACK_VALUES, M2_ARRAY.size, "track values")
        if not sub_arrays or (global_sequence < 0 and not self.first_sequence_inline):
            return range(0)
        count, start = M2_ARRAY.unpack_from(self.view.data, sub_arrays[0])
        if count == 0 or not self.view.contains(start, count * layout.size):
            return range(0)
        return range(start, start + count * layout.size, layout.size)

    def first_key(self, offset: int, layout: struct.Struct) -> Optional[tuple]:
        keys = self.first_keys(offset, layout)
        return layout.unpack_from(self.view.data, keys[0]) if keys else None

    def first_scalar(self, offset: int, layout: struct.Struct, default: float) -> float:
        key = self.first_key(offset, layout)
        return default if key is None else key[0]

    def peak_scalar(self, offset: int, layout: struct.Struct, default: float) -> float:
        values = [layout.unpack_from(self.view.data, key)[0] for key in self.first_keys(offset, layout)]
        values = [value for value in values if not math.isnan(value)]
        return max(values) if values else default


def first_sequence_inline(view: BinaryView, offset: int) -> bool:
    sequences = view.elements(offset, M2_SEQUENCE_SIZE, "sequences")
    if not sequences:
        return False
    return bool(U32.unpack_from(view.data, sequences[0] + SEQUENCE_FLAGS)[0] & SEQUENCE_INLINE)


class RestPose:
    def __init__(self, view: BinaryView, bones_offset: int, tracks: TrackReader):
        self.view = view
        self.tracks = tracks
        self.bones = view.elements(bones_offset, M2_BONE_SIZE, "bones")
        self.cache: Dict[int, Affine] = {}

    def parent(self, bone: int) -> int:
        return I16.unpack_from(self.view.data, self.bones[bone] + BONE_PARENT)[0]

    def local(self, bone: int) -> Affine:
        offset = self.bones[bone]
        translation = self.tracks.first_key(offset + BONE_TRANSLATION, VEC3) or ORIGIN
        compressed = self.tracks.first_key(offset + BONE_ROTATION, COMPRESSED_QUATERNION)
        rotation = decompressed_quaternion(compressed) if compressed else IDENTITY_QUATERNION
        scale = self.tracks.first_key(offset + BONE_SCALE, VEC3) or UNIT_SCALE
        pivot = VEC3.unpack_from(self.view.data, offset + BONE_PIVOT)
        return pivoted_affine(pivot, translation, rotation, scale)

    def transform(self, bone: int) -> Affine:
        chain: List[int] = []
        visited = set()
        current = bone
        while 0 <= current < len(self.bones) and current not in self.cache and current not in visited:
            chain.append(current)
            visited.add(current)
            current = self.parent(current)
        base = self.cache.get(current, IDENTITY_AFFINE)
        for index in reversed(chain):
            base = compose_affine(base, self.local(index))
            self.cache[index] = base
        return self.cache.get(bone, IDENTITY_AFFINE)

    def place(self, bone: int, position: Vec3) -> Vec3:
        return apply_affine(self.transform(bone), position)


def read_textures(view: BinaryView, offset: int) -> List[str]:
    textures = []
    for record in view.elements(offset, M2_TEXTURE.size, "textures"):
        texture_type, _, length, start = M2_TEXTURE.unpack_from(view.data, record)
        if texture_type != TEXTURE_FILE:
            textures.append("")
            continue
        view.require(start, length, "texture file name")
        textures.append(decoded(view.data[start:start + length].split(b"\0", 1)[0]))
    return textures


def indexed(items: Sequence, index: int, label: str, what: str):
    if index < 0 or index >= len(items):
        raise FormatError("%s: %s %d is outside its table of %d" % (label, what, index, len(items)))
    return items[index]


def read_light(view: BinaryView, offset: int, tracks: TrackReader, pose: RestPose) -> M2Light:
    light_type, bone, x, y, z = LIGHT_HEAD.unpack_from(view.data, offset)
    visibility = tracks.first_key(offset + LIGHT_VISIBILITY, U8)
    return M2Light(light_type=light_type, bone=bone, position=pose.place(bone, (x, y, z)),
                   diffuse_color=tracks.first_key(offset + LIGHT_DIFFUSE_COLOR, VEC3) or ORIGIN,
                   diffuse_intensity=tracks.first_scalar(offset + LIGHT_DIFFUSE_INTENSITY, F32, 0.0),
                   attenuation_start=tracks.first_scalar(offset + LIGHT_ATTENUATION_START, F32, 0.0),
                   attenuation_end=tracks.first_scalar(offset + LIGHT_ATTENUATION_END, F32, 0.0),
                   visible=visibility is None or visibility[0] != 0)


def fake_track_values(view: BinaryView, offset: int, layout: struct.Struct, what: str) -> List[tuple]:
    return [layout.unpack_from(view.data, value)
            for value in view.elements(offset + FAKE_TRACK_VALUES, layout.size, what)]


def emitter_texture(textures: Sequence[str], index: int, notes: List[str]) -> str:
    if index < len(textures):
        return textures[index]
    note = "emitter texture %d is outside the table of %d" % (index, len(textures))
    if note not in notes:
        notes.append(note)
    return ""


def read_emitter(view: BinaryView, offset: int, tracks: TrackReader, pose: RestPose, textures: Sequence[str],
                 notes: List[str]) -> M2Emitter:
    _, _, x, y, z, bone, texture = EMITTER_HEAD.unpack_from(view.data, offset)
    blend = U8.unpack_from(view.data, offset + EMITTER_BLEND)[0]
    colors = fake_track_values(view, offset + EMITTER_COLOR, VEC3, "emitter colours")
    alphas = fake_track_values(view, offset + EMITTER_ALPHA, I16, "emitter alphas")
    sizes = fake_track_values(view, offset + EMITTER_SCALE, VEC2, "emitter sizes")
    return M2Emitter(bone=bone, position=pose.place(bone, (x, y, z)),
                     texture=emitter_texture(textures, texture, notes), blend=blend,
                     emission_rate=tracks.peak_scalar(offset + EMITTER_EMISSION_RATE, F32, 0.0),
                     colors=[tuple(channel / COLOR_CHANNEL_MAX for channel in color) for color in colors],
                     alphas=[alpha[0] / FIXED16_ONE for alpha in alphas], sizes=[size[0] for size in sizes])


def skin_path(model_path: str) -> Optional[str]:
    if not model_path.lower().endswith(MODEL_SUFFIX):
        return None
    return model_path[:-len(MODEL_SUFFIX)] + "00.skin"


def read_batches(view: BinaryView, layout: HeaderLayout, textures: Sequence[str], skin: bytes) -> List[M2Batch]:
    skin_view = BinaryView(skin, view.label + " skin")
    if skin[:len(SKIN_MAGIC)] != SKIN_MAGIC:
        raise FormatError("%s: magic %r is not SKIN" % (skin_view.label, skin[:len(SKIN_MAGIC)]))
    submeshes = skin_view.elements(SKIN_SUBMESHES, SKIN_SUBMESH_SIZE, "submeshes")
    units = skin_view.elements(SKIN_BATCHES, SKIN_BATCH_SIZE, "batches")
    materials = [M2_MATERIAL.unpack_from(view.data, offset)
                 for offset in view.elements(layout.materials, M2_MATERIAL.size, "materials")]
    lookup = [U16.unpack_from(view.data, offset)[0]
              for offset in view.elements(layout.texture_lookup, U16.size, "texture lookup")]
    batches = []
    for unit in units:
        values = SKIN_BATCH.unpack_from(skin, unit)
        submesh, material, combo = values[3], values[6], values[9]
        submesh_offset = indexed(submeshes, submesh, skin_view.label, "batch submesh")
        material_flags, blend = indexed(materials, material, view.label, "batch material")
        texture = indexed(textures, indexed(lookup, combo, view.label, "texture combo"), view.label,
                          "batch texture")
        batches.append(M2Batch(unlit=bool(material_flags & MATERIAL_UNLIT), blend=blend, texture=texture,
                               center=VEC3.unpack_from(skin, submesh_offset + SUBMESH_CENTER),
                               index_count=U16.unpack_from(skin, submesh_offset + SUBMESH_INDEX_COUNT)[0]))
    return batches


def model_batches(view: BinaryView, layout: HeaderLayout, textures: Sequence[str],
                  skin: Optional[bytes]) -> Tuple[List[M2Batch], List[str]]:
    if not skin:
        return [], ["no skin"]
    try:
        return read_batches(view, layout, textures, skin), []
    except FormatError as error:
        return [], ["batches unreadable: %s" % error]


def parse_m2(path: str, data: bytes, skin: Optional[bytes] = None) -> ParsedM2Model:
    view = BinaryView(data, path)
    magic, version = view.unpack(M2_PREAMBLE, 0, "header")
    if magic != M2_MAGIC:
        raise FormatError("%s: magic %r is not MD20" % (path, magic))
    layout, notes = header_layout(version)
    model = ParsedM2Model(path=path, version=version,
                          bounds_min=view.unpack(VEC3, layout.bounds_min, "bounding box"),
                          bounds_max=view.unpack(VEC3, layout.bounds_max, "bounding box"),
                          textures=read_textures(view, layout.textures), notes=notes)
    if layout.lights is None:
        return model
    tracks = TrackReader(view, first_sequence_inline(view, layout.sequences))
    pose = RestPose(view, layout.bones, tracks)
    model.lights = [read_light(view, offset, tracks, pose)
                    for offset in view.elements(layout.lights, M2_LIGHT_SIZE, "lights")]
    model.emitters = [read_emitter(view, offset, tracks, pose, model.textures, model.notes)
                      for offset in view.elements(layout.emitters, layout.emitter_size, "particle emitters")]
    model.batches, batch_notes = model_batches(view, layout, model.textures, skin)
    model.notes.extend(batch_notes)
    return model


def m2_light_count(data: bytes) -> int:
    view = BinaryView(data, "M2")
    magic, version = view.unpack(M2_PREAMBLE, 0, "header")
    if magic != M2_MAGIC:
        raise FormatError("M2: magic %r is not MD20" % magic)
    layout, _ = header_layout(version)
    return view.unpack(M2_ARRAY, LEGACY_LIGHT_COUNT if layout.lights is None else layout.lights, "lights")[0]
