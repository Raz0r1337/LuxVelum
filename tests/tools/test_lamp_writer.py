import math
import os
import random
import struct
import tempfile
import unittest
from dataclasses import replace

import lamp_data_fixture as fixture
import lamp_writer as lw
from lamp_types import (FLAG_WMO_DOODAD, KIND_CANDLE, KIND_CHANDELIER, KIND_LAMP, KIND_TORCH, ROUTE_AUTHORED,
                        ROUTE_EMISSIVE, ROUTE_FLAME, ROUTE_NAME, ROUTE_RESTORED, ArchiveSource, Lamp)

HEADER_SIZE = 32
SOURCE_SIZE = 72
MAP_SIZE = 20
CELL_SIZE = 12
LAMP_SIZE = 32


def lamp(position, route=ROUTE_FLAME, map_id=0, color=(1.0, 0.5, 0.25), reach=12.0, kind=KIND_TORCH, flags=0):
    return Lamp(map_id=map_id, position=position, color=color, reach=reach, kind=kind, route=route, flags=flags)


def file_size(sources, maps, cells, lamps):
    return HEADER_SIZE + sources * SOURCE_SIZE + maps * MAP_SIZE + cells * CELL_SIZE + lamps * LAMP_SIZE


def without_model(lamps):
    return [replace(item, model="") for item in lamps]


class Layout(unittest.TestCase):
    def test_record_sizes_are_those_the_dll_reads(self):
        self.assertEqual((lw.HEADER.size, lw.SOURCE.size, lw.MAP.size, lw.CELL.size, lw.LAMP.size),
                         (HEADER_SIZE, SOURCE_SIZE, MAP_SIZE, CELL_SIZE, LAMP_SIZE))

    def test_header_and_record_order(self):
        sources = [ArchiveSource("common.MPQ", 10, False), ArchiveSource("enUS/patch-enUS-4.MPQ", 2 ** 40, True)]
        lamps = [lamp((100.0, 200.0, 5.0)), lamp((-5000.0, 300.0, 6.0), map_id=530),
                 lamp((100.5, 200.0, 7.0), ROUTE_NAME, kind=KIND_LAMP)]
        data = lw.lamp_data_bytes(lamps, sources)
        self.assertEqual(len(data), file_size(2, 2, 2, 3))
        self.assertEqual(struct.unpack_from("<4s7I", data, 0), (b"LXLD", 1, 2, 2, 3, 2, 0, 0))
        name, size = struct.unpack_from("<64sQ", data, HEADER_SIZE + SOURCE_SIZE)
        self.assertEqual((name.rstrip(b"\0"), size), (b"enUS\\patch-enUS-4.MPQ", 2 ** 40))
        maps = HEADER_SIZE + 2 * SOURCE_SIZE
        self.assertEqual(struct.unpack_from("<5I", data, maps), (0, 0, 1, 0, 2))
        self.assertEqual(struct.unpack_from("<5I", data, maps + MAP_SIZE), (530, 1, 1, 2, 1))
        cells = maps + 2 * MAP_SIZE
        x, y = lw.cell_of(100.0), lw.cell_of(200.0)
        self.assertEqual(struct.unpack_from("<2H2I", data, cells), (x, y, 0, 2))
        first = struct.unpack_from("<3f3ffHBB", data, cells + 2 * CELL_SIZE)
        self.assertEqual(first, (100.0, 200.0, 5.0, 1.0, 0.5, 0.25, 12.0, 0, KIND_TORCH, ROUTE_FLAME))

    def test_long_and_non_ascii_source_names_are_cut_to_63_bytes(self):
        long_name = "Custom/" + "x" * 80 + ".MPQ"
        data = lw.lamp_data_bytes([], [ArchiveSource(long_name, 1, True), ArchiveSource("pätch-Ä.MPQ", 2, True)])
        sources = lw.read_lamp_data(data).sources
        self.assertEqual(sources[0].path, ("Custom\\" + "x" * 80)[:63])
        self.assertEqual(struct.unpack_from("<64s", data, HEADER_SIZE)[0][63:], b"\0")
        self.assertEqual(sources[1], lw.SourceRecord("p?tch-?.MPQ", 2))

    def test_an_empty_file_is_a_header(self):
        data = lw.lamp_data_bytes([])
        self.assertEqual(data, struct.pack("<4s7I", b"LXLD", 1, 0, 0, 0, 0, 0, 0))
        self.assertEqual(lw.read_lamp_data(data).lamps, [])


class RoundTrip(unittest.TestCase):
    def test_lamps_come_back_by_map_and_cell_rounded_to_float32(self):
        lamps = [lamp((x * 61.7, y * 47.3 - 900.0, x - y), ROUTE_AUTHORED + (x + y) % 5, map_id=(0, 1, 571)[x % 3],
                      color=(0.1 * x, 0.2, 0.3 * y), reach=1.0 + x + y, kind=(x * y) % 7, flags=x % 32)
                 for x in range(12) for y in range(9)]
        sources = [ArchiveSource("common.MPQ", 123, False), ArchiveSource("patch-A.MPQ", 456, True)]
        read = lw.read_lamp_data(lw.lamp_data_bytes(lamps, sources))
        self.assertEqual(read.sources, [lw.SourceRecord("common.MPQ", 123), lw.SourceRecord("patch-A.MPQ", 456)])
        self.assertEqual([record.map_id for record in read.maps], [0, 1, 571])
        expected = sorted((lw.stored_lamp(item) for item in lamps), key=lw.lamp_order)
        self.assertEqual(read.lamps, expected)
        for record in read.maps:
            self.assertEqual(read.map_lamps(record.map_id), [item for item in expected if item.map_id == record.map_id])
        for cell in read.cells:
            for item in read.lamps[cell.first_lamp:cell.first_lamp + cell.lamp_count]:
                self.assertEqual(lw.cell_key(item), (cell.x, cell.y))
        keys = [(cell.x, cell.y) for cell in read.cells[read.maps[0].first_cell:read.maps[1].first_cell]]
        self.assertEqual(keys, sorted(set(keys)))
        self.assertEqual(read.lamps[-1].color, tuple(lw.float32(value) for value in read.lamps[-1].color))

    def test_the_bytes_do_not_depend_on_the_order_of_the_lamps(self):
        lamps = [lamp((float(index), float(index % 7) * 140.0, 1.0), ROUTE_AUTHORED + index % 5, map_id=index % 2)
                 for index in range(40)]
        lamps.append(lamp((3.0, 3 * 140.0, 1.0), ROUTE_NAME, map_id=1, kind=KIND_LAMP))
        shuffled = list(lamps)
        random.Random(7).shuffle(shuffled)
        self.assertEqual(lw.lamp_data_bytes(lamps), lw.lamp_data_bytes(shuffled))

    def test_write_lamp_data_creates_the_folder_and_leaves_no_partial_file(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "Data", "LuxVelum", "lampdata.bin")
            data = lw.write_lamp_data(path, [lamp((1.0, 2.0, 3.0))])
            self.assertEqual(os.listdir(os.path.dirname(path)), ["lampdata.bin"])
            self.assertEqual(lw.read_lamp_data_file(path).lamps, [lw.stored_lamp(lamp((1.0, 2.0, 3.0)))])
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), data)


class Cells(unittest.TestCase):
    def test_cells_are_133_yard_squares_from_the_map_corner_and_clamped(self):
        self.assertEqual(lw.cell_of(-17066.0), 0)
        self.assertEqual(lw.cell_of(-17068.0), 0)
        self.assertEqual(lw.cell_of(0.0), 127)
        self.assertEqual(lw.cell_of(1.0), 128)
        self.assertEqual(lw.cell_of(17060.0), 255)
        self.assertEqual(lw.cell_of(17068.0), 255)
        self.assertEqual(lw.cell_of(-17066.666 + 133.33333 * 10 + 0.001), 10)
        self.assertEqual(lw.cell_of(-17066.666 + 133.33333 * 10 - 0.001), 9)

    def test_cells_follow_the_stored_float32_position_as_the_dll_computes_them(self):
        straddling = None
        for index in range(1, 256):
            edge = index * 133.33333 - 17066.666
            for offset in (1e-4, 2e-4, 4e-4, 8e-4):
                candidate = edge - offset
                if lw.cell_of(lw.float32(candidate)) != lw.cell_of(candidate):
                    straddling = candidate
                    break
            if straddling is not None:
                break
        self.assertIsNotNone(straddling)
        data = lw.lamp_data_bytes([lamp((straddling, 0.0, 0.0)), lamp((0.0, straddling, 0.0))])
        read = lw.read_lamp_data(data)
        self.assertEqual([(cell.x, cell.y) for cell in read.cells],
                         sorted([(lw.cell_of(lw.float32(straddling)), lw.cell_of(0.0)),
                                 (lw.cell_of(0.0), lw.cell_of(lw.float32(straddling)))]))


class WriterAssertions(unittest.TestCase):
    def assertRefused(self, lamps, sources=(), text=None):
        with self.assertRaises(lw.LampDataError) as raised:
            lw.lamp_data_bytes(lamps, sources)
        if text is not None:
            self.assertIn(text, str(raised.exception))

    def test_every_out_of_range_lamp_is_refused(self):
        good = lamp((10.0, 20.0, 30.0))
        self.assertEqual(len(lw.lamp_data_bytes([good])), file_size(0, 1, 1, 1))
        broken = [
            replace(good, position=(math.nan, 20.0, 30.0)), replace(good, position=(10.0, math.inf, 30.0)),
            replace(good, color=(1.0, math.nan, 0.0)), replace(good, reach=math.inf),
            replace(good, position=(17068.5, 20.0, 30.0)), replace(good, position=(10.0, -17069.0, 30.0)),
            replace(good, position=(10.0, 20.0, 20001.0)), replace(good, position=(10.0, 20.0, -20001.0)),
            replace(good, reach=0.0), replace(good, reach=-1.0), replace(good, reach=200.5),
            replace(good, color=(-0.1, 0.0, 0.0)), replace(good, color=(64.5, 0.0, 0.0)),
            replace(good, kind=7), replace(good, kind=-1), replace(good, kind=1.0), replace(good, route=0),
            replace(good, route=6), replace(good, flags=0x10000), replace(good, map_id=-1),
            replace(good, map_id=2 ** 32), replace(good, position=(1.0, 2.0)),
        ]
        for item in broken:
            with self.subTest(lamp=item):
                self.assertRefused([good, item])

    def test_the_limits_themselves_are_stored(self):
        edges = [lamp((-17068.0, 17068.0, 20000.0), reach=200.0, color=(64.0, 0.0, 64.0)),
                 lamp((17068.0, -17068.0, -20000.0), reach=1e-3, color=(0.0, 0.0, 0.0), kind=KIND_CHANDELIER,
                      route=ROUTE_EMISSIVE, flags=0xFFFF, map_id=2 ** 32 - 1)]
        read = lw.read_lamp_data(lw.lamp_data_bytes(edges))
        self.assertEqual(sorted(cell.x for cell in read.cells), [0, 255])
        self.assertEqual(read.maps[-1].map_id, 2 ** 32 - 1)

    def test_a_value_that_rounds_into_range_in_float32_is_stored(self):
        read = lw.read_lamp_data(lw.lamp_data_bytes([lamp((17068.0004, 0.0, 0.0), reach=200.000001)]))
        self.assertEqual((read.lamps[0].position[0], read.lamps[0].reach), (17068.0, 200.0))

    def test_too_many_sources_and_bad_sizes_are_refused(self):
        sources = [ArchiveSource("patch-x.MPQ", 1, True)] * 1024
        self.assertEqual(len(lw.read_lamp_data(lw.lamp_data_bytes([], sources)).sources), 1024)
        self.assertRefused([], sources + [ArchiveSource("patch-y.MPQ", 1, True)], "1025 source archives")
        self.assertRefused([], [ArchiveSource("patch-y.MPQ", -1, True)])
        self.assertRefused([], [ArchiveSource("patch-y.MPQ", 2 ** 64, True)])


class ReaderRejections(unittest.TestCase):
    def good(self):
        return bytearray(fixture.fixture_bytes())

    def layout(self, data):
        _, _, maps, cells, lamps, sources, _, _ = struct.unpack_from("<4s7I", data, 0)
        map_start = HEADER_SIZE + sources * SOURCE_SIZE
        cell_start = map_start + maps * MAP_SIZE
        return map_start, cell_start, cell_start + cells * CELL_SIZE

    def assertRejected(self, data, text):
        with self.assertRaises(lw.LampDataError) as raised:
            lw.read_lamp_data(bytes(data))
        self.assertIn(text, str(raised.exception))

    def test_broken_files_are_rejected_as_the_dll_rejects_them(self):
        good = self.good()
        maps, cells, lamps = self.layout(good)
        self.assertEqual(len(lw.read_lamp_data(bytes(good)).lamps), 10)
        self.assertRejected(good[:31], "shorter than its header")
        self.assertRejected(b"LXLE" + good[4:], "not a lamp data file")
        self.assertRejected(good[:4] + struct.pack("<I", 2) + good[8:], "format version 2")
        self.assertRejected(good[:-1], "truncated or padded")
        self.assertRejected(good + b"\0", "truncated or padded")
        swapped = self.good()
        second = maps + MAP_SIZE
        swapped[maps:maps + 4], swapped[second:second + 4] = good[second:second + 4], good[maps:maps + 4]
        self.assertRejected(swapped, "maps out of order")
        empty_cell = self.good()
        struct.pack_into("<I", empty_cell, cells + 8, 0)
        self.assertRejected(empty_cell, "cells of map 0")
        moved = self.good()
        struct.pack_into("<f", moved, lamps, 99.0)
        self.assertRejected(moved, "outside its cell")
        far = self.good()
        struct.pack_into("<f", far, lamps + 8, 20001.0)
        self.assertRejected(far, "beyond the world's edge")
        unknown_route = self.good()
        struct.pack_into("<B", unknown_route, lamps + 31, 6)
        self.assertRejected(unknown_route, "unknown route 6")
        many = self.good()
        struct.pack_into("<I", many, 20, 1025)
        self.assertRejected(many, "more than 1024 source archives")


class Preparation(unittest.TestCase):
    def test_out_of_range_values_are_brought_into_range_and_unstorable_lamps_dropped(self):
        bright = lamp((1.0, 2.0, 3.0), color=(128.0, 64.0, -1.0), reach=450.0)
        fine = lamp((4.0, 5.0, 6.0))
        dropped = [lamp((math.nan, 0.0, 0.0)), lamp((0.0, 0.0, 0.0), color=(math.inf, 0.0, 0.0)),
                   lamp((0.0, 0.0, 0.0), reach=0.0), lamp((0.0, 0.0, 0.0), reach=1e-50),
                   lamp((17100.0, 0.0, 0.0)), lamp((0.0, 0.0, 25000.0))]
        prepared = lw.prepare_lamps([bright, fine] + dropped)
        self.assertEqual((prepared.clamped, prepared.dropped), (1, len(dropped)))
        self.assertEqual(prepared.lamps[0].color, (64.0, 32.0, 0.0))
        self.assertEqual(prepared.lamps[0].reach, 200.0)
        self.assertEqual(prepared.lamps[1], fine)
        self.assertEqual(len(lw.read_lamp_data(lw.lamp_data_bytes(prepared.lamps)).lamps), 2)


class Fixture(unittest.TestCase):
    def test_the_committed_fixture_is_what_the_writer_makes_of_the_fixed_list(self):
        with open(fixture.FIXTURE_PATH, "rb") as handle:
            committed = handle.read()
        self.assertEqual(fixture.fixture_bytes(), committed)

    def test_the_fixture_holds_two_maps_several_cells_every_route_and_every_kind(self):
        read = lw.read_lamp_data(fixture.fixture_bytes())
        self.assertEqual(len(read.lamps), 10)
        self.assertEqual([(record.map_id, record.cell_count, record.lamp_count) for record in read.maps],
                         [(0, 4, 6), (530, 3, 4)])
        self.assertEqual(len(read.cells), 7)
        self.assertEqual({item.route for item in read.lamps},
                         {ROUTE_AUTHORED, ROUTE_RESTORED, ROUTE_FLAME, ROUTE_NAME, ROUTE_EMISSIVE})
        self.assertEqual({item.kind for item in read.lamps}, set(range(7)))
        self.assertEqual(read.lamps[0], replace(lw.stored_lamp(fixture.FIXTURE_LAMPS[-1]), model=""))
        self.assertEqual(read.lamps[0].color[0], lw.float32(0.6))
        self.assertEqual((read.cells[0].x, read.cells[0].y), (0, 255))
        self.assertEqual(read.lamps[5].flags, FLAG_WMO_DOODAD)
        self.assertEqual(read.sources[3].path, "enUS\\patch-enUS-Z-with-a-rather-long-name-for-the-sixty-three-b")
        self.assertEqual(read.sources[2].size, 5000000000)
        self.assertEqual(read.lamps[7].kind, KIND_CANDLE)


if __name__ == "__main__":
    unittest.main()
