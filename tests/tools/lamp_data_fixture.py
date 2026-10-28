import os
import sys

from lamp_types import (FLAG_BOUNDS_FALLBACK, FLAG_CLAMPED_TO_MODEL, FLAG_DEAD_AUTHORED_BLOCKS, FLAG_GLOBAL_WMO,
                        FLAG_WMO_DOODAD, KIND_BONFIRE, KIND_BRAZIER, KIND_CANDLE, KIND_CHANDELIER, KIND_LAMP,
                        KIND_TORCH, KIND_UNKNOWN, ROUTE_AUTHORED, ROUTE_EMISSIVE, ROUTE_FLAME, ROUTE_NAME,
                        ROUTE_RESTORED, ArchiveSource, Lamp)
from lamp_writer import lamp_data_bytes

AZEROTH = 0
OUTLAND = 530
FIXTURE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data",
                            "lampdata-fixture.bin")

FIXTURE_SOURCES = [
    ArchiveSource("common.MPQ", 2919102541, False),
    ArchiveSource("enUS/patch-enUS-3.MPQ", 123456, False),
    ArchiveSource("patch-A.MPQ", 5000000000, True),
    ArchiveSource("enUS/patch-enUS-Z-with-a-rather-long-name-for-the-sixty-three-byte-cut.MPQ", 77, True),
]

FIXTURE_LAMPS = [
    Lamp(OUTLAND, (3000.0, 2000.0, 150.0), (64.0, 32.0, 0.0), 200.0, KIND_UNKNOWN, ROUTE_RESTORED, 0),
    Lamp(AZEROTH, (-8833.5, 622.25, 93.75), (1.0, 0.75, 0.5), 12.0, KIND_LAMP, ROUTE_AUTHORED, 0),
    Lamp(OUTLAND, (-1838.5, 5302.0, -12.0), (3.0, 1.5, 0.75), 24.0, KIND_BONFIRE, ROUTE_FLAME, FLAG_GLOBAL_WMO),
    Lamp(AZEROTH, (-4981.0, -881.0, 505.0), (0.75, 0.5, 0.25), 6.0, KIND_CHANDELIER, ROUTE_EMISSIVE,
         FLAG_WMO_DOODAD),
    Lamp(AZEROTH, (-8830.0, 625.5, 94.0), (0.5, 0.25, 0.125), 8.5, KIND_TORCH, ROUTE_RESTORED,
         FLAG_DEAD_AUTHORED_BLOCKS),
    Lamp(OUTLAND, (-248.5, 932.25, 84.5), (1.0, 0.5, 0.0), 20.0, KIND_TORCH, ROUTE_AUTHORED, 0),
    Lamp(AZEROTH, (-9000.25, 400.5, 60.0), (2.0, 1.25, 0.5), 16.0, KIND_BRAZIER, ROUTE_FLAME, FLAG_CLAMPED_TO_MODEL),
    Lamp(AZEROTH, (-4981.25, -881.5, 501.75), (1.5, 1.125, 0.625), 12.0, KIND_LAMP, ROUTE_NAME,
         FLAG_WMO_DOODAD | FLAG_BOUNDS_FALLBACK),
    Lamp(OUTLAND, (-1838.0, 5301.5, -12.25), (0.625, 0.75, 1.0), 6.0, KIND_CANDLE, ROUTE_NAME, 0),
    Lamp(AZEROTH, (-17066.5, 17060.25, -250.0), (0.6, 0.35, 0.1), 6.0, KIND_CANDLE, ROUTE_FLAME, 0),
]


def fixture_bytes() -> bytes:
    return lamp_data_bytes(FIXTURE_LAMPS, FIXTURE_SOURCES)


def write_fixture(path: str = FIXTURE_PATH) -> int:
    data = fixture_bytes()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return len(data)


if __name__ == "__main__":
    sys.exit(0 if write_fixture() else 1)
