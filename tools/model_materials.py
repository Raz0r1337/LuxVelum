import struct
from dataclasses import dataclass, field
from typing import List, NamedTuple, Optional, Sequence, Tuple

from lamp_formats import (FIXED16_ONE, I16, M2_ARRAY, M2_MAGIC, M2_MATERIAL, M2_PREAMBLE, M2_SEQUENCE_SIZE,
                          M2_TEXTURE, MOHD, SEQUENCE_FLAGS, SEQUENCE_INLINE, SKIN_BATCH_SIZE, SKIN_BATCHES,
                          SKIN_MAGIC, SKIN_SUBMESH_SIZE, SKIN_SUBMESHES, SUBMESH_INDEX_COUNT, TEXTURE_FILE,
                          TRACK_HEAD, TRACK_VALUES, U16, U32, VEC3, WDBC_HEADER, WDBC_MAGIC, WOTLK_LAYOUT,
                          WOTLK_VERSION, BinaryView, FormatError, chunk_bytes, decoded, first_chunks, records,
                          string_at)
from lamp_types import Vec3

M2_GLOBAL_FLAGS = 0x10
M2_SKIN_PROFILES = 0x44
M2_COLORS = 0x48
M2_TEXTURE_WEIGHTS = 0x58
M2_TEXTURE_UNIT_LOOKUP = 0x88
M2_TRANSPARENCY_LOOKUP = 0x90
M2_COMBINER_COMBOS = 0x130
GLOBAL_FLAG_COMBINER_COMBOS = 0x8
M2_COLOR_SIZE = 40
COLOR_ALPHA = 20
M2_TEXTURE_WEIGHT_SIZE = 20
SKIN_BATCH_RECORD = struct.Struct("<BbHHHhHHHHHHH")
NO_COLOR = -1
MAX_BATCH_TEXTURES = 4

MOTX = b"MOTX"
MOMT = b"MOMT"
MFOG = b"MFOG"
MOHD_RECORD = struct.Struct("<9I6f2H")
MOMT_RECORD = struct.Struct("<16I")
MFOG_RECORD = struct.Struct("<I3f4fIffI")

WORLD_MAP_AREA_PREFIX = struct.Struct("<4I4f")
WORLD_MAP_AREA_FIELDS = 11
WORLD_MAP_AREA_RECORD_SIZE = 44


class TrackKeys(NamedTuple):
    values: List
    external_sequences: int
    outside_file: int


@dataclass
class M2Texture:
    texture_type: int
    flags: int
    name: str


@dataclass
class BatchTexture:
    texture: Optional[M2Texture]
    coord: Optional[int]


@dataclass
class RenderBatch:
    flags: int
    priority: int
    shader: int
    submesh: int
    index_count: Optional[int]
    color: int
    material: int
    material_flags: Optional[int]
    blend: Optional[int]
    layer: int
    texture_count: int
    textures: List[BatchTexture] = field(default_factory=list)
    weight_lookup: int = 0
    weight: Optional[int] = None
    combiner_combos: List[int] = field(default_factory=list)
    color_rgb: Optional[TrackKeys] = None
    color_alpha: Optional[TrackKeys] = None
    transparency: Optional[TrackKeys] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class M2Materials:
    version: int
    global_flags: int = 0
    skin_profiles: int = 0
    bounds_min: Vec3 = (0.0, 0.0, 0.0)
    bounds_max: Vec3 = (0.0, 0.0, 0.0)
    sequences: int = 0
    external_sequences: int = 0
    textures: List[M2Texture] = field(default_factory=list)
    batches: List[RenderBatch] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class WmoMaterial:
    flags: int
    shader: int
    blend: int
    textures: List[str]
    sidn_color: int
    diffuse_color: int
    ground_type: int


@dataclass
class WmoFog:
    flags: int
    position: Vec3
    small_radius: float
    large_radius: float
    end: float
    start_factor: float
    color: int
    underwater_end: float
    underwater_start_factor: float
    underwater_color: int


@dataclass
class WmoDetails:
    groups: int
    flags: int
    ambient_color: int
    materials: List[WmoMaterial] = field(default_factory=list)
    fogs: List[WmoFog] = field(default_factory=list)


@dataclass
class WorldMapArea:
    record_id: int
    map_id: int
    area_id: int
    name: str
    left: float
    right: float
    top: float
    bottom: float


class WorldMapAreaTable(NamedTuple):
    areas: List[WorldMapArea]
    fields: int
    record_size: int


def entry(items: Sequence, index: int):
    return items[index] if 0 <= index < len(items) else None


def inline_sequences(view: BinaryView) -> List[bool]:
    return [bool(U32.unpack_from(view.data, offset + SEQUENCE_FLAGS)[0] & SEQUENCE_INLINE)
            for offset in view.elements(WOTLK_LAYOUT.sequences, M2_SEQUENCE_SIZE, "sequences")]


def track_keys(view: BinaryView, offset: int, layout: struct.Struct, inline: Sequence[bool]) -> TrackKeys:
    _, global_sequence = view.unpack(TRACK_HEAD, offset, "track")
    values = []
    external = 0
    outside = 0
    for index, sub_array in enumerate(view.elements(offset + TRACK_VALUES, M2_ARRAY.size, "track values")):
        count, start = M2_ARRAY.unpack_from(view.data, sub_array)
        if count == 0:
            continue
        if global_sequence < 0 and not entry(inline, index):
            external += 1
            continue
        if not view.contains(start, count * layout.size):
            outside += 1
            continue
        values.extend(layout.unpack_from(view.data, start + key * layout.size) for key in range(count))
    return TrackKeys(values, external, outside)


def fixed16_keys(keys: TrackKeys) -> TrackKeys:
    return keys._replace(values=[value[0] / FIXED16_ONE for value in keys.values])


def vector_keys(keys: TrackKeys) -> TrackKeys:
    return keys._replace(values=[tuple(value) for value in keys.values])


def texture_entries(view: BinaryView) -> List[M2Texture]:
    textures = []
    for offset in view.elements(WOTLK_LAYOUT.textures, M2_TEXTURE.size, "textures"):
        texture_type, flags, length, start = M2_TEXTURE.unpack_from(view.data, offset)
        name = ""
        if texture_type == TEXTURE_FILE and length:
            view.require(start, length, "texture file name")
            name = decoded(view.data[start:start + length].split(b"\0", 1)[0])
        textures.append(M2Texture(texture_type, flags, name))
    return textures


def unpacked_list(view: BinaryView, offset: int, layout: struct.Struct, what: str) -> List:
    return [layout.unpack_from(view.data, element)[0] for element in view.elements(offset, layout.size, what)]


def combiner_combos(view: BinaryView, global_flags: int) -> List[int]:
    if not global_flags & GLOBAL_FLAG_COMBINER_COMBOS:
        return []
    return unpacked_list(view, M2_COMBINER_COMBOS, U16, "texture combiner combos")


class M2Tables:
    def __init__(self, view: BinaryView, global_flags: int):
        self.view = view
        self.inline = inline_sequences(view)
        self.textures = texture_entries(view)
        self.colors = view.elements(M2_COLORS, M2_COLOR_SIZE, "colours")
        self.weights = view.elements(M2_TEXTURE_WEIGHTS, M2_TEXTURE_WEIGHT_SIZE, "texture weights")
        self.materials = [M2_MATERIAL.unpack_from(view.data, offset)
                          for offset in view.elements(WOTLK_LAYOUT.materials, M2_MATERIAL.size, "materials")]
        self.texture_lookup = unpacked_list(view, WOTLK_LAYOUT.texture_lookup, U16, "texture lookup")
        self.unit_lookup = unpacked_list(view, M2_TEXTURE_UNIT_LOOKUP, I16, "texture unit lookup")
        self.transparency_lookup = unpacked_list(view, M2_TRANSPARENCY_LOOKUP, U16, "transparency lookup")
        self.combos = combiner_combos(view, global_flags)

    def color_tracks(self, index: int) -> Tuple[Optional[TrackKeys], Optional[TrackKeys]]:
        offset = entry(self.colors, index)
        if offset is None:
            return None, None
        return (vector_keys(track_keys(self.view, offset, VEC3, self.inline)),
                fixed16_keys(track_keys(self.view, offset + COLOR_ALPHA, I16, self.inline)))

    def weight_track(self, index: Optional[int]) -> Optional[TrackKeys]:
        offset = None if index is None else entry(self.weights, index)
        if offset is None:
            return None
        return fixed16_keys(track_keys(self.view, offset, I16, self.inline))

    def batch_texture(self, slot: int, coord_slot: int) -> BatchTexture:
        texture_index = entry(self.texture_lookup, slot)
        texture = None if texture_index is None else entry(self.textures, texture_index)
        return BatchTexture(texture, entry(self.unit_lookup, coord_slot))


def batch_notes(batch: RenderBatch, tables: M2Tables, texture_combo: int, coord_combo: int) -> List[str]:
    notes = []
    if batch.texture_count > MAX_BATCH_TEXTURES:
        notes.append("texture count %d is above %d; the first %d are shown"
                     % (batch.texture_count, MAX_BATCH_TEXTURES, MAX_BATCH_TEXTURES))
    if batch.blend is None:
        notes.append("material %d is outside the table of %d" % (batch.material, len(tables.materials)))
    if batch.color != NO_COLOR and batch.color_alpha is None:
        notes.append("colour %d is outside the table of %d" % (batch.color, len(tables.colors)))
    if batch.weight is None:
        notes.append("transparency lookup %d is outside the table of %d"
                     % (batch.weight_lookup, len(tables.transparency_lookup)))
    elif batch.transparency is None:
        notes.append("texture weight %d is outside the table of %d" % (batch.weight, len(tables.weights)))
    for layer, texture in enumerate(batch.textures):
        if texture.texture is None:
            notes.append("texture %d (lookup %d) is outside the tables" % (layer, texture_combo + layer))
        if texture.coord is None:
            notes.append("texture %d coordinates (lookup %d) are outside the table" % (layer, coord_combo + layer))
    return notes


def render_batch(record: tuple, tables: M2Tables, submesh_counts: Sequence[int]) -> RenderBatch:
    (flags, priority, shader, submesh, _, color, material, layer, texture_count, texture_combo, coord_combo,
     weight_combo, _) = record
    material_entry = entry(tables.materials, material)
    material_flags, blend = material_entry if material_entry is not None else (None, None)
    weight = entry(tables.transparency_lookup, weight_combo)
    color_rgb, color_alpha = tables.color_tracks(color) if color != NO_COLOR else (None, None)
    slots = range(min(texture_count, MAX_BATCH_TEXTURES))
    batch = RenderBatch(flags=flags, priority=priority, shader=shader, submesh=submesh,
                        index_count=entry(submesh_counts, submesh), color=color, material=material,
                        material_flags=material_flags, blend=blend, layer=layer, texture_count=texture_count,
                        textures=[tables.batch_texture(texture_combo + slot, coord_combo + slot) for slot in slots],
                        weight_lookup=weight_combo, weight=weight,
                        combiner_combos=[combo for combo in (entry(tables.combos, shader + slot) for slot in slots)
                                         if combo is not None],
                        color_rgb=color_rgb, color_alpha=color_alpha, transparency=tables.weight_track(weight))
    batch.notes = batch_notes(batch, tables, texture_combo, coord_combo)
    return batch


def skin_batches(label: str, skin: bytes, tables: M2Tables) -> List[RenderBatch]:
    view = BinaryView(skin, label + " skin")
    if skin[:len(SKIN_MAGIC)] != SKIN_MAGIC:
        raise FormatError("%s: magic %r is not SKIN" % (view.label, skin[:len(SKIN_MAGIC)]))
    submesh_counts = [U16.unpack_from(skin, offset + SUBMESH_INDEX_COUNT)[0]
                      for offset in view.elements(SKIN_SUBMESHES, SKIN_SUBMESH_SIZE, "submeshes")]
    return [render_batch(SKIN_BATCH_RECORD.unpack_from(skin, offset), tables, submesh_counts)
            for offset in view.elements(SKIN_BATCHES, SKIN_BATCH_SIZE, "batches")]


def parse_m2_materials(path: str, data: bytes, skin: Optional[bytes]) -> M2Materials:
    view = BinaryView(data, path)
    magic, version = view.unpack(M2_PREAMBLE, 0, "header")
    if magic != M2_MAGIC:
        raise FormatError("%s: magic %r is not MD20" % (path, magic))
    if version < WOTLK_VERSION:
        return M2Materials(version, notes=["version %d predates the WotLK header; materials not read" % version])
    global_flags = view.unpack(U32, M2_GLOBAL_FLAGS, "global flags")[0]
    tables = M2Tables(view, global_flags)
    materials = M2Materials(version, global_flags=global_flags,
                            skin_profiles=view.unpack(U32, M2_SKIN_PROFILES, "skin profiles")[0],
                            bounds_min=view.unpack(VEC3, WOTLK_LAYOUT.bounds_min, "bounding box"),
                            bounds_max=view.unpack(VEC3, WOTLK_LAYOUT.bounds_max, "bounding box"),
                            sequences=len(tables.inline), external_sequences=tables.inline.count(False),
                            textures=tables.textures)
    if version != WOTLK_VERSION:
        materials.notes.append("version %d: read with the WotLK header" % version)
    if not skin:
        materials.notes.append("no skin")
        return materials
    try:
        materials.batches = skin_batches(path, skin, tables)
    except FormatError as error:
        materials.notes.append("batches unreadable: %s" % error)
    return materials


def wmo_texture_names(textures: bytes, offsets: Sequence[int]) -> List[str]:
    names = []
    for slot, offset in enumerate(offsets):
        name = string_at(textures, offset) if slot == 0 or offset else None
        if name:
            names.append(name)
    return names


def wmo_material(values: tuple, textures: bytes) -> WmoMaterial:
    (flags, shader, blend, texture_1, sidn_color, _, texture_2, diffuse_color, ground_type, texture_3) = values[:10]
    return WmoMaterial(flags=flags, shader=shader, blend=blend,
                       textures=wmo_texture_names(textures, (texture_1, texture_2, texture_3)),
                       sidn_color=sidn_color, diffuse_color=diffuse_color, ground_type=ground_type)


def wmo_fog(values: tuple) -> WmoFog:
    return WmoFog(flags=values[0], position=values[1:4], small_radius=values[4], large_radius=values[5],
                  end=values[6], start_factor=values[7], color=values[8], underwater_end=values[9],
                  underwater_start_factor=values[10], underwater_color=values[11])


def parse_wmo_details(data: bytes, label: str = "WMO") -> WmoDetails:
    view = BinaryView(data, label)
    found = first_chunks(view)
    if MOHD not in found:
        raise FormatError("%s: no MOHD chunk, so this is not a WMO root" % label)
    header = chunk_bytes(view, found, MOHD)
    if len(header) < MOHD_RECORD.size:
        raise FormatError("%s: MOHD holds %d bytes instead of %d" % (label, len(header), MOHD_RECORD.size))
    values = MOHD_RECORD.unpack_from(header, 0)
    textures = chunk_bytes(view, found, MOTX)
    material_block = chunk_bytes(view, found, MOMT)
    fog_block = chunk_bytes(view, found, MFOG)
    return WmoDetails(groups=values[1], flags=values[15], ambient_color=values[7],
                      materials=[wmo_material(MOMT_RECORD.unpack_from(material_block, offset), textures)
                                 for offset in records(material_block, MOMT_RECORD)],
                      fogs=[wmo_fog(MFOG_RECORD.unpack_from(fog_block, offset))
                            for offset in records(fog_block, MFOG_RECORD)])


def parse_world_map_area_dbc(data: bytes) -> WorldMapAreaTable:
    view = BinaryView(data, "WorldMapArea.dbc")
    magic, count, fields, record_size, string_size = view.unpack(WDBC_HEADER, 0, "header")
    if magic != WDBC_MAGIC:
        raise FormatError("WorldMapArea.dbc: magic %r is not WDBC" % magic)
    if count and record_size < WORLD_MAP_AREA_PREFIX.size:
        raise FormatError("WorldMapArea.dbc: records of %d bytes cannot hold an area and its bounds" % record_size)
    strings_start = WDBC_HEADER.size + count * record_size
    view.require(strings_start, string_size, "string block")
    strings = data[strings_start:strings_start + string_size]
    areas = []
    for index in range(count):
        values = WORLD_MAP_AREA_PREFIX.unpack_from(data, WDBC_HEADER.size + index * record_size)
        name = string_at(strings, values[3])
        if name is None:
            raise FormatError("WorldMapArea.dbc: record %d names offset %d outside the string block"
                              % (values[0], values[3]))
        areas.append(WorldMapArea(values[0], values[1], values[2], name, *values[4:8]))
    return WorldMapAreaTable(areas, fields, record_size)
