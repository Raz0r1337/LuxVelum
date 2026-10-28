from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Vec3 = Tuple[float, float, float]
Matrix3 = Tuple[Vec3, Vec3, Vec3]

ROUTE_AUTHORED = 1
ROUTE_RESTORED = 2
ROUTE_FLAME = 3
ROUTE_NAME = 4
ROUTE_EMISSIVE = 5
ROUTE_NAMES = {ROUTE_AUTHORED: "authored", ROUTE_RESTORED: "restored", ROUTE_FLAME: "flame", ROUTE_NAME: "name",
               ROUTE_EMISSIVE: "emissive"}

KIND_UNKNOWN = 0
KIND_CANDLE = 1
KIND_TORCH = 2
KIND_BRAZIER = 3
KIND_BONFIRE = 4
KIND_LAMP = 5
KIND_CHANDELIER = 6
KIND_NAMES = {KIND_UNKNOWN: "unknown", KIND_CANDLE: "candle", KIND_TORCH: "torch", KIND_BRAZIER: "brazier",
              KIND_BONFIRE: "bonfire", KIND_LAMP: "lamp", KIND_CHANDELIER: "chandelier"}

FLAG_WMO_DOODAD = 0x1
FLAG_BOUNDS_FALLBACK = 0x2
FLAG_CLAMPED_TO_MODEL = 0x4
FLAG_GLOBAL_WMO = 0x8
FLAG_DEAD_AUTHORED_BLOCKS = 0x10

IDENTITY: Matrix3 = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


@dataclass
class M2Light:
    light_type: int
    bone: int
    position: Vec3
    diffuse_color: Vec3
    diffuse_intensity: float
    attenuation_start: float
    attenuation_end: float
    visible: bool


@dataclass
class M2Emitter:
    bone: int
    position: Vec3
    texture: str
    blend: int
    emission_rate: float
    colors: List[Vec3] = field(default_factory=list)
    alphas: List[float] = field(default_factory=list)
    sizes: List[float] = field(default_factory=list)


@dataclass
class M2Batch:
    unlit: bool
    blend: int
    texture: str
    center: Vec3
    index_count: int


@dataclass
class M2Model:
    path: str
    version: int
    bounds_min: Vec3
    bounds_max: Vec3
    textures: List[str] = field(default_factory=list)
    lights: List[M2Light] = field(default_factory=list)
    emitters: List[M2Emitter] = field(default_factory=list)
    batches: List[M2Batch] = field(default_factory=list)


@dataclass
class ModelLamp:
    position: Vec3
    color: Vec3
    intensity: float
    reach: float
    kind: int
    route: int
    flags: int = 0


@dataclass
class ModelVerdict:
    route: Optional[int]
    lamps: List[ModelLamp] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class Placement:
    model: str
    position: Vec3
    rotation: Matrix3
    scale: float
    unique_id: int
    flags: int = 0


@dataclass
class Lamp:
    map_id: int
    position: Vec3
    color: Vec3
    reach: float
    kind: int
    route: int
    flags: int
    model: str = ""


@dataclass
class ArchiveSource:
    name: str
    size: int
    custom: bool
