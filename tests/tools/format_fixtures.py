import struct
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]

M2_HEADER_SIZE = 0x130
LEGACY_M2_HEADER_SIZE = 0x144
SKIN_HEADER_SIZE = 48
DETACHED_OFFSET = 0x7FFFFF00
ARRAY_ALIGNMENT = 16
SEQUENCE_INLINE = 0x20
MAP_DBC_FIELDS = 66
MAP_DBC_RECORD_SIZE = MAP_DBC_FIELDS * 4
WDT_GRID = 64
ADT_VERSION = 18
WMO_VERSION = 17
MCIN_ENTRIES = 256
MCIN_ENTRY_SIZE = 16


def pack(layout: str, *values) -> bytes:
    return struct.pack("<" + layout, *values)


def chunk(magic: bytes, payload: bytes) -> bytes:
    return magic[::-1] + pack("I", len(payload)) + payload


def string_block(names: Sequence[str]) -> Tuple[bytes, List[int]]:
    block = b""
    offsets = []
    for name in names:
        offsets.append(len(block))
        block += name.encode("ascii") + b"\0"
    return block, offsets


def compressed_component(value: float) -> int:
    scaled_value = int(round(value * 32767))
    return scaled_value - 32768 if value > 0 else scaled_value + 32767


def compressed_quaternion(q: Sequence[float]) -> Tuple[int, int, int, int]:
    return tuple(compressed_component(component) for component in q)


class Arena:
    def __init__(self, reserved: int):
        self.data = bytearray(reserved)

    def append(self, payload: bytes) -> int:
        self.data.extend(b"\0" * (-len(self.data) % ARRAY_ALIGNMENT))
        offset = len(self.data)
        self.data.extend(payload)
        return offset

    def array(self, count: int, payload: bytes) -> bytes:
        return pack("2I", count, self.append(payload) if count else 0)

    def string(self, text: str) -> bytes:
        if not text:
            return pack("2I", 0, 0)
        encoded = text.encode("ascii") + b"\0"
        return self.array(len(encoded), encoded)

    def track(self, layout: str, keys_per_sequence: Sequence[Sequence[Sequence]], global_sequence: int = -1,
              detached: Iterable[int] = ()) -> bytes:
        detached = set(detached)
        stamps = b""
        values = b""
        for index, keys in enumerate(keys_per_sequence):
            stamps += self.array(len(keys), b"".join(pack("I", time * 100) for time in range(len(keys))))
            if index in detached:
                values += pack("2I", len(keys), DETACHED_OFFSET)
            else:
                values += self.array(len(keys), b"".join(pack(layout, *key) for key in keys))
        sequences = len(keys_per_sequence)
        return pack("Hh", 0, global_sequence) + self.array(sequences, stamps) + self.array(sequences, values)

    def single_key_track(self, layout: str, key: Optional[Sequence], global_sequence: int = -1,
                         detached: bool = False) -> bytes:
        if key is None:
            return self.track(layout, [])
        return self.track(layout, [[key]], global_sequence, (0,) if detached else ())

    def fake_track(self, layout: str, keys: Sequence[Sequence]) -> bytes:
        stamps = b"".join(pack("H", index * 16383) for index in range(len(keys)))
        return self.array(len(keys), stamps) + self.array(len(keys), b"".join(pack(layout, *key) for key in keys))


@dataclass
class SequenceSpec:
    flags: int = SEQUENCE_INLINE
    animation: int = 0
    duration: int = 1000


@dataclass
class BoneSpec:
    parent: int = -1
    pivot: Vec3 = (0.0, 0.0, 0.0)
    translation: Optional[Vec3] = None
    rotation: Optional[Tuple[float, float, float, float]] = None
    scale: Optional[Vec3] = None
    global_sequence: int = -1
    detached: bool = False


@dataclass
class TextureSpec:
    filename: str = ""
    texture_type: int = 0
    flags: int = 0


@dataclass
class LightSpec:
    light_type: int = 1
    bone: int = -1
    position: Vec3 = (0.0, 0.0, 0.0)
    ambient_color: Optional[Vec3] = (0.0, 0.0, 0.0)
    ambient_intensity: Optional[float] = 0.0
    diffuse_color: Optional[Vec3] = (1.0, 0.5, 0.25)
    diffuse_intensity: Optional[float] = 1.0
    attenuation_start: Optional[float] = 1.0
    attenuation_end: Optional[float] = 5.0
    visibility: Optional[int] = None
    global_sequence: int = -1


@dataclass
class EmitterSpec:
    bone: int = 0
    position: Vec3 = (0.0, 0.0, 0.0)
    texture: int = 0
    blend: int = 4
    emitter_type: int = 1
    emission_rate: Optional[float] = 20.0
    emission_rate_keys: Optional[List[float]] = None
    colors: List[Vec3] = field(default_factory=lambda: [(255.0, 128.0, 0.0), (255.0, 64.0, 0.0)])
    alphas: List[int] = field(default_factory=lambda: [32767, 0])
    sizes: List[Tuple[float, float]] = field(default_factory=lambda: [(0.5, 0.5), (0.25, 0.25)])


@dataclass
class KeyTrackSpec:
    keys_per_sequence: List[List[Sequence]] = field(default_factory=list)
    global_sequence: int = -1
    detached: Tuple[int, ...] = ()


@dataclass
class ColorSpec:
    rgb: KeyTrackSpec = field(default_factory=lambda: KeyTrackSpec([[(1.0, 1.0, 1.0)]]))
    alpha: KeyTrackSpec = field(default_factory=lambda: KeyTrackSpec([[(32767,)]]))


@dataclass
class SubmeshSpec:
    center: Vec3 = (0.0, 0.0, 0.0)
    index_count: int = 0
    index_start: int = 0


@dataclass
class BatchSpec:
    submesh: int = 0
    material: int = 0
    texture_combo: int = 0
    flags: int = 0
    shader: int = 0
    color: int = -1
    texture_count: int = 1
    texture_coord_combo: int = 0
    texture_weight_combo: int = 0
    priority: int = 0
    layer: int = 0


@dataclass
class M2Spec:
    version: int = 264
    name: str = "Fixture"
    bounds_min: Vec3 = (-1.0, -1.0, 0.0)
    bounds_max: Vec3 = (1.0, 1.0, 2.0)
    sequences: List[SequenceSpec] = field(default_factory=lambda: [SequenceSpec()])
    bones: List[BoneSpec] = field(default_factory=list)
    textures: List[TextureSpec] = field(default_factory=list)
    materials: List[Tuple[int, int]] = field(default_factory=list)
    texture_lookup: List[int] = field(default_factory=list)
    lights: List[LightSpec] = field(default_factory=list)
    emitters: List[EmitterSpec] = field(default_factory=list)
    global_flags: int = 0
    colors: List[ColorSpec] = field(default_factory=list)
    texture_weights: List[KeyTrackSpec] = field(default_factory=list)
    texture_unit_lookup: List[int] = field(default_factory=list)
    transparency_lookup: List[int] = field(default_factory=list)
    combiner_combos: Optional[List[int]] = None


def sequence_record(spec: SequenceSpec) -> bytes:
    record = (pack("HHIfIhH", spec.animation, 0, spec.duration, 0.0, spec.flags, 32767, 0) + pack("2I", 0, 0)
              + pack("I", 150) + pack("7f", -1.0, -1.0, -1.0, 1.0, 1.0, 1.0, 2.0) + pack("hH", -1, 0))
    assert len(record) == 64
    return record


def bone_record(arena: Arena, spec: BoneSpec) -> bytes:
    rotation = None if spec.rotation is None else compressed_quaternion(spec.rotation)
    record = (pack("iIhHI", -1, 0, spec.parent, 0, 0)
              + arena.single_key_track("3f", spec.translation, spec.global_sequence, spec.detached)
              + arena.single_key_track("4h", rotation, spec.global_sequence, spec.detached)
              + arena.single_key_track("3f", spec.scale, spec.global_sequence, spec.detached)
              + pack("3f", *spec.pivot))
    assert len(record) == 88
    return record


def scalar(value: Optional[float]) -> Optional[Tuple[float]]:
    return None if value is None else (value,)


def light_record(arena: Arena, spec: LightSpec) -> bytes:
    sequence = spec.global_sequence
    record = (pack("Hh3f", spec.light_type, spec.bone, *spec.position)
              + arena.single_key_track("3f", spec.ambient_color, sequence)
              + arena.single_key_track("f", scalar(spec.ambient_intensity), sequence)
              + arena.single_key_track("3f", spec.diffuse_color, sequence)
              + arena.single_key_track("f", scalar(spec.diffuse_intensity), sequence)
              + arena.single_key_track("f", scalar(spec.attenuation_start), sequence)
              + arena.single_key_track("f", scalar(spec.attenuation_end), sequence)
              + arena.single_key_track("B", scalar(spec.visibility), sequence))
    assert len(record) == 156
    return record


def emission_rate_track(arena: Arena, spec: EmitterSpec) -> bytes:
    if spec.emission_rate_keys is None:
        return arena.single_key_track("f", scalar(spec.emission_rate))
    return arena.track("f", [[(rate,) for rate in spec.emission_rate_keys]])


def particle_record(arena: Arena, spec: EmitterSpec) -> bytes:
    empty_float_track = arena.track("f", [])
    record = (pack("II3fHH", 0xFFFFFFFF, 0, *spec.position, spec.bone, spec.texture)
              + arena.string("") + arena.string("")
              + pack("BBH", spec.blend, spec.emitter_type, 0)
              + pack("BB", 0, 0)
              + pack("3H", 0, 1, 1)
              + empty_float_track * 6
              + pack("f", 0.0)
              + emission_rate_track(arena, spec)
              + pack("f", 0.0)
              + empty_float_track * 3
              + arena.fake_track("3f", spec.colors)
              + arena.fake_track("h", [(alpha,) for alpha in spec.alphas])
              + arena.fake_track("2f", spec.sizes)
              + pack("2f", 0.0, 0.0)
              + arena.fake_track("H", []) + arena.fake_track("H", [])
              + pack("3f", 0.0, 0.0, 0.0) + pack("2f", 0.0, 0.0)
              + pack("2f", 0.0, 0.0)
              + pack("4f", 0.0, 0.0, 0.0, 0.0)
              + pack("6f", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
              + pack("3f", 0.0, 0.0, 0.0) + pack("f", 0.0)
              + pack("4f", 0.0, 0.0, 0.0, 0.0)
              + arena.array(0, b"")
              + arena.track("B", []))
    assert len(record) == 476
    return record


def texture_record(arena: Arena, spec: TextureSpec) -> bytes:
    record = pack("II", spec.texture_type, spec.flags) + arena.string(spec.filename)
    assert len(record) == 16
    return record


def records_array(arena: Arena, records: Sequence[bytes]) -> bytes:
    return arena.array(len(records), b"".join(records))


def key_track(arena: Arena, layout: str, spec: KeyTrackSpec) -> bytes:
    return arena.track(layout, spec.keys_per_sequence, spec.global_sequence, spec.detached)


def color_record(arena: Arena, spec: ColorSpec) -> bytes:
    record = key_track(arena, "3f", spec.rgb) + key_track(arena, "h", spec.alpha)
    assert len(record) == 40
    return record


def m2_bytes(spec: M2Spec) -> bytes:
    header_size = M2_HEADER_SIZE + (8 if spec.combiner_combos is not None else 0)
    arena = Arena(header_size)
    empty = pack("2I", 0, 0)
    sequences = records_array(arena, [sequence_record(sequence) for sequence in spec.sequences])
    bones = records_array(arena, [bone_record(arena, bone) for bone in spec.bones])
    colors = records_array(arena, [color_record(arena, color) for color in spec.colors])
    textures = records_array(arena, [texture_record(arena, texture) for texture in spec.textures])
    weights = records_array(arena, [key_track(arena, "h", weight) for weight in spec.texture_weights])
    materials = records_array(arena, [pack("HH", flags, blend) for flags, blend in spec.materials])
    texture_lookup = records_array(arena, [pack("H", index) for index in spec.texture_lookup])
    unit_lookup = records_array(arena, [pack("h", index) for index in spec.texture_unit_lookup])
    transparency_lookup = records_array(arena, [pack("H", index) for index in spec.transparency_lookup])
    lights = records_array(arena, [light_record(arena, light) for light in spec.lights])
    emitters = records_array(arena, [particle_record(arena, emitter) for emitter in spec.emitters])
    combos = b""
    if spec.combiner_combos is not None:
        combos = records_array(arena, [pack("H", combo) for combo in spec.combiner_combos])
    name = arena.string(spec.name)
    header = (b"MD20" + pack("I", spec.version) + name + pack("I", spec.global_flags)
              + empty + sequences + empty
              + bones + empty + empty
              + pack("I", 1)
              + colors + textures + weights + empty + empty
              + materials + empty + texture_lookup + unit_lookup + transparency_lookup + empty
              + pack("3f", *spec.bounds_min) + pack("3f", *spec.bounds_max) + pack("f", 2.0)
              + pack("6f", *spec.bounds_min, *spec.bounds_max) + pack("f", 2.0)
              + empty + empty + empty + empty + empty + empty
              + lights + empty + empty + empty + emitters + combos)
    assert len(header) == header_size
    arena.data[:header_size] = header
    return bytes(arena.data)


def legacy_m2_bytes(version: int, bounds_min: Vec3, bounds_max: Vec3, textures: Sequence[TextureSpec]) -> bytes:
    arena = Arena(LEGACY_M2_HEADER_SIZE)
    empty = pack("2I", 0, 0)
    texture_array = records_array(arena, [texture_record(arena, texture) for texture in textures])
    lights = arena.array(1, b"\0" * 212)
    header = (b"MD20" + pack("I", version) + empty + pack("I", 0)
              + empty + empty + empty + empty
              + empty + empty + empty
              + empty
              + empty + texture_array + empty + empty + empty
              + empty + empty + empty + empty + empty + empty + empty
              + pack("3f", *bounds_min) + pack("3f", *bounds_max) + pack("f", 1.0)
              + pack("6f", *bounds_min, *bounds_max) + pack("f", 1.0)
              + empty + empty + empty + empty + empty + empty
              + lights + empty + empty + empty + empty)
    assert len(header) == LEGACY_M2_HEADER_SIZE
    arena.data[:LEGACY_M2_HEADER_SIZE] = header
    return bytes(arena.data)


def submesh_record(spec: SubmeshSpec) -> bytes:
    record = (pack("10H", 0, 0, 0, 0, spec.index_start, spec.index_count, 0, 0, 1, 0)
              + pack("3f", *spec.center) + pack("3f", *spec.center) + pack("f", 1.0))
    assert len(record) == 48
    return record


def batch_record(spec: BatchSpec) -> bytes:
    record = pack("BbHHHhHHHHHHH", spec.flags, spec.priority, spec.shader, spec.submesh, 0, spec.color,
                  spec.material, spec.layer, spec.texture_count, spec.texture_combo, spec.texture_coord_combo,
                  spec.texture_weight_combo, 0)
    assert len(record) == 24
    return record


def skin_bytes(submeshes: Sequence[SubmeshSpec], batches: Sequence[BatchSpec]) -> bytes:
    arena = Arena(SKIN_HEADER_SIZE)
    empty = pack("2I", 0, 0)
    submesh_array = records_array(arena, [submesh_record(submesh) for submesh in submeshes])
    batch_array = records_array(arena, [batch_record(batch) for batch in batches])
    header = b"SKIN" + empty + empty + empty + submesh_array + batch_array + pack("I", 0)
    assert len(header) == SKIN_HEADER_SIZE
    arena.data[:SKIN_HEADER_SIZE] = header
    return bytes(arena.data)


def world_map_area_dbc_bytes(areas: Sequence[Tuple[int, int, int, str, float, float, float, float]]) -> bytes:
    strings = b"\0"
    records = b""
    for record_id, map_id, area_id, name, left, right, top, bottom in areas:
        records += pack("4I4f3i", record_id, map_id, area_id, len(strings), left, right, top, bottom, -1, 0, -1)
        strings += name.encode("ascii") + b"\0"
    return pack("4s4I", b"WDBC", len(areas), 11, 44, len(strings)) + records + strings


def map_dbc_bytes(maps: Sequence[Tuple[int, str]]) -> bytes:
    strings = b"\0"
    records = b""
    for map_id, directory in maps:
        record = pack("II", map_id, len(strings)) + b"\0" * (MAP_DBC_RECORD_SIZE - 8)
        strings += directory.encode("ascii") + b"\0"
        records += record
    return pack("4s4I", b"WDBC", len(maps), MAP_DBC_FIELDS, MAP_DBC_RECORD_SIZE, len(strings)) + records + strings


@dataclass
class DoodadPlacement:
    name_id: int
    unique_id: int
    position: Vec3
    rotation: Vec3 = (0.0, 0.0, 0.0)
    scale: int = 1024
    flags: int = 0


@dataclass
class WmoPlacement:
    name_id: int
    unique_id: int
    position: Vec3
    rotation: Vec3 = (0.0, 0.0, 0.0)
    extents_min: Vec3 = (0.0, 0.0, 0.0)
    extents_max: Vec3 = (0.0, 0.0, 0.0)
    flags: int = 0
    doodad_set: int = 0
    name_set: int = 0


def mddf_record(placement: DoodadPlacement) -> bytes:
    return pack("2I3f3fHH", placement.name_id, placement.unique_id, *placement.position, *placement.rotation,
                placement.scale, placement.flags)


def modf_record(placement: WmoPlacement) -> bytes:
    return pack("2I3f3f3f3fHHHH", placement.name_id, placement.unique_id, *placement.position,
                *placement.rotation, *placement.extents_min, *placement.extents_max, placement.flags,
                placement.doodad_set, placement.name_set, 0)


def wdt_bytes(tiles: Iterable[Tuple[int, int]], global_wmo: Optional[str] = None,
              global_placement: Optional[WmoPlacement] = None, flags: Optional[int] = None) -> bytes:
    present = set(tiles)
    main = b"".join(pack("2I", 1 if (x, y) in present else 0, 0) for y in range(WDT_GRID) for x in range(WDT_GRID))
    mphd_flags = (1 if global_wmo else 0) if flags is None else flags
    data = chunk(b"MVER", pack("I", ADT_VERSION)) + chunk(b"MPHD", pack("8I", mphd_flags, 0, 0, 0, 0, 0, 0, 0))
    data += chunk(b"MAIN", main)
    data += chunk(b"MWMO", string_block([global_wmo])[0] if global_wmo else b"")
    if global_placement is not None:
        data += chunk(b"MODF", modf_record(global_placement))
    return data


def adt_bytes(m2_names: Sequence[str], wmo_names: Sequence[str], doodads: Sequence[DoodadPlacement],
              wmos: Sequence[WmoPlacement], textures: Sequence[str] = ("Tileset\\Fixture.blp",)) -> bytes:
    mmdx, mmid = string_block(m2_names)
    mwmo, mwid = string_block(wmo_names)
    body_chunks = [
        (b"MCIN", b"\0" * (MCIN_ENTRIES * MCIN_ENTRY_SIZE)),
        (b"MTEX", string_block(textures)[0]),
        (b"MMDX", mmdx),
        (b"MMID", b"".join(pack("I", offset) for offset in mmid)),
        (b"MWMO", mwmo),
        (b"MWID", b"".join(pack("I", offset) for offset in mwid)),
        (b"MDDF", b"".join(mddf_record(doodad) for doodad in doodads)),
        (b"MODF", b"".join(modf_record(wmo) for wmo in wmos)),
    ]
    mver = chunk(b"MVER", pack("I", ADT_VERSION))
    mhdr_data_start = len(mver) + 8
    cursor = mhdr_data_start + 64
    offsets: Dict[bytes, int] = {}
    body = b""
    for magic, payload in body_chunks:
        offsets[magic] = cursor + len(body) - mhdr_data_start
        body += chunk(magic, payload)
    mhdr = pack("16I", 0, offsets[b"MCIN"], offsets[b"MTEX"], offsets[b"MMDX"], offsets[b"MMID"], offsets[b"MWMO"],
                offsets[b"MWID"], offsets[b"MDDF"], offsets[b"MODF"], 0, 0, 0, 0, 0, 0, 0)
    dummy_cell = chunk(b"MCNK", b"\xAB" * 136)
    return mver + chunk(b"MHDR", mhdr) + body + dummy_cell


@dataclass
class WmoDoodadSpec:
    name: str
    position: Vec3 = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: float = 1.0
    flags: int = 0
    color: int = 0xFF7F7F7F


@dataclass
class WmoMaterialSpec:
    flags: int = 0
    shader: int = 0
    blend: int = 0
    texture: str = ""
    second_texture: str = ""
    sidn_color: int = 0
    diffuse_color: int = 0
    ground_type: int = 0


@dataclass
class WmoFogSpec:
    flags: int = 0
    position: Vec3 = (0.0, 0.0, 0.0)
    small_radius: float = 0.0
    large_radius: float = 0.0
    end: float = 444.5
    start_factor: float = 0.25
    color: int = 0xFF000000
    underwater_end: float = 222.25
    underwater_start_factor: float = -0.5
    underwater_color: int = 0xFF000000


def wmo_material_record(spec: WmoMaterialSpec, offsets: Dict[str, int]) -> bytes:
    second = offsets[spec.second_texture] if spec.second_texture else 0
    record = pack("16I", spec.flags, spec.shader, spec.blend, offsets.get(spec.texture, 0), spec.sidn_color, 0,
                  second, spec.diffuse_color, spec.ground_type, 0, 0, 0, 0, 0, 0, 0)
    assert len(record) == 64
    return record


def wmo_fog_record(spec: WmoFogSpec) -> bytes:
    record = pack("I3f4fIffI", spec.flags, *spec.position, spec.small_radius, spec.large_radius, spec.end,
                  spec.start_factor, spec.color, spec.underwater_end, spec.underwater_start_factor,
                  spec.underwater_color)
    assert len(record) == 48
    return record


def wmo_root_bytes(doodad_sets: Sequence[Tuple[str, int, int]], doodads: Sequence[WmoDoodadSpec],
                   materials: Sequence[WmoMaterialSpec] = (), fogs: Optional[Sequence[WmoFogSpec]] = None,
                   flags: int = 0, groups: int = 0) -> bytes:
    names, offsets = string_block([doodad.name for doodad in doodads])
    texture_names = list(dict.fromkeys(name for material in materials
                                       for name in (material.texture, material.second_texture) if name))
    textures, texture_offsets = string_block(texture_names)
    mohd = pack("7I", len(texture_names), groups, 0, 0, 0, len(doodads), len(doodad_sets))
    mohd += pack("4B", 0, 0, 0, 255) + pack("I", 0)
    mohd += pack("6f", -1.0, -1.0, -1.0, 1.0, 1.0, 1.0) + pack("HH", flags, 0)
    assert len(mohd) == 64
    mods = b"".join(pack("20s3I", name.encode("ascii"), start, count, 0) for name, start, count in doodad_sets)
    modd = b"".join(pack("I3f4ffI", (doodad.flags << 24) | offset, *doodad.position, *doodad.rotation,
                         doodad.scale, doodad.color) for doodad, offset in zip(doodads, offsets))
    momt = b""
    if materials:
        texture_offset = dict(zip(texture_names, texture_offsets))
        momt = chunk(b"MOMT", b"".join(wmo_material_record(material, texture_offset) for material in materials))
    fog_block = b"\0" * 48 if fogs is None else b"".join(wmo_fog_record(fog) for fog in fogs)
    return (chunk(b"MVER", pack("I", WMO_VERSION)) + chunk(b"MOHD", mohd) + chunk(b"MOTX", textures) + momt
            + chunk(b"MODS", mods) + chunk(b"MODN", names) + chunk(b"MODD", modd)
            + chunk(b"MFOG", fog_block))
