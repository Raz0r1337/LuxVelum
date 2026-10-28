import math
import unittest
from collections import Counter

import format_fixtures as fx
import lamp_world as lw
from lamp_mpq import MpqError, VersionRead
from lamp_formats import Mddf, Modf, WmoDoodad, WmoRoot, DoodadSet
from lamp_types import (FLAG_BOUNDS_FALLBACK, FLAG_GLOBAL_WMO, FLAG_WMO_DOODAD, IDENTITY, KIND_CANDLE, KIND_LAMP,
                        KIND_TORCH, ROUTE_AUTHORED, ROUTE_FLAME, ROUTE_NAME, ROUTE_RESTORED, ArchiveSource, Lamp,
                        ModelLamp, ModelVerdict, Placement)

MID = 32 * 533.33333
QUARTER_TURN_Z = (0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5))
STOCK = ArchiveSource("common.MPQ", 100, False)
PATCH = ArchiveSource("patch-3.MPQ", 100, False)
CUSTOM = ArchiveSource("patch-A.MPQ", 100, True)


def mddf(position, rotation=(0.0, 0.0, 0.0), scale=1024, unique_id=1, name="World\\Lamp.m2"):
    return Mddf(name_id=0, unique_id=unique_id, position=position, rotation=rotation, scale=scale, flags=0,
                name=name)


def modf(position, rotation=(0.0, 0.0, 0.0), unique_id=21, doodad_set=0, name="World\\wmo\\Inn.wmo"):
    return Modf(name_id=0, unique_id=unique_id, position=position, rotation=rotation, extents_min=(0.0, 0.0, 0.0),
                extents_max=(0.0, 0.0, 0.0), flags=0, doodad_set=doodad_set, name_set=0, name=name)


class Geometry(unittest.TestCase):
    def assertPoint(self, actual, expected, places=4):
        self.assertEqual(len(actual), 3)
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, places=places)

    def assertMatrix(self, actual, expected):
        for row_a, row_e in zip(actual, expected):
            self.assertPoint(row_a, row_e)


class DoodadTransforms(Geometry):
    def test_zero_rotation(self):
        placement = lw.placement_from_mddf(mddf((100.0, 50.0, 200.0), unique_id=7))
        self.assertPoint(placement.position, (MID - 200.0, MID - 100.0, 50.0))
        self.assertMatrix(placement.rotation, ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)))
        self.assertEqual((placement.scale, placement.unique_id, placement.model), (1.0, 7, "World\\Lamp.m2"))
        self.assertPoint(lw.transform_point(placement, (1.0, 2.0, 3.0)), (MID - 201.0, MID - 102.0, 53.0))

    def test_yaw_of_ninety_degrees(self):
        placement = lw.placement_from_mddf(mddf((100.0, 50.0, 200.0), (0.0, 90.0, 0.0)))
        origin = (MID - 200.0, MID - 100.0, 50.0)
        self.assertPoint(lw.transform_point(placement, (1.0, 0.0, 0.0)), (origin[0], origin[1] - 1.0, 50.0))
        self.assertPoint(lw.transform_point(placement, (0.0, 1.0, 0.0)), (origin[0] + 1.0, origin[1], 50.0))

    def test_pitch_and_roll(self):
        origin = (MID, MID, 0.0)
        pitch = lw.placement_from_mddf(mddf((0.0, 0.0, 0.0), (90.0, 0.0, 0.0)))
        self.assertPoint(lw.transform_point(pitch, (1.0, 0.0, 0.0)), (origin[0], origin[1], -1.0))
        roll = lw.placement_from_mddf(mddf((0.0, 0.0, 0.0), (0.0, 0.0, 90.0)))
        self.assertPoint(lw.transform_point(roll, (0.0, 1.0, 0.0)), (origin[0], origin[1], 1.0))

    def test_rotation_order_is_yaw_pitch_roll(self):
        origin = (MID, MID, 0.0)
        yaw_pitch = lw.placement_from_mddf(mddf((0.0, 0.0, 0.0), (90.0, 90.0, 0.0)))
        self.assertPoint(lw.transform_point(yaw_pitch, (0.0, 0.0, 1.0)), (origin[0], origin[1] - 1.0, 0.0))
        pitch_roll = lw.placement_from_mddf(mddf((0.0, 0.0, 0.0), (90.0, 0.0, 90.0)))
        self.assertPoint(lw.transform_point(pitch_roll, (0.0, 1.0, 0.0)), (origin[0] - 1.0, origin[1], 0.0))

    def test_scale(self):
        placement = lw.placement_from_mddf(mddf((100.0, 50.0, 200.0), scale=2048))
        self.assertEqual(placement.scale, 2.0)
        self.assertPoint(lw.transform_point(placement, (1.0, 0.0, 0.5)), (MID - 202.0, MID - 100.0, 51.0))


def inn_root():
    sets = [DoodadSet("Set_$DefaultGlobal", 0, 2), DoodadSet("Set_Party", 2, 1), DoodadSet("Set_Night", 3, 4)]
    doodads = [WmoDoodad("World\\Lamp.m2", (5.0, 0.0, 1.0), QUARTER_TURN_Z, 0.5),
               WmoDoodad("World\\Chair.m2", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 1.0),
               WmoDoodad("World\\Banner.m2", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 1.0),
               WmoDoodad("World\\Candle.m2", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), 1.0)]
    return WmoRoot(sets, doodads)


class WmoTransforms(Geometry):
    def test_wmo_rotation_and_doodad_quaternion(self):
        wmo = lw.placement_from_modf(modf((1000.0, 10.0, 2000.0), (0.0, 90.0, 0.0), unique_id=21))
        self.assertPoint(wmo.position, (MID - 2000.0, MID - 1000.0, 10.0))
        lamp_doodad = lw.wmo_doodad_placements(wmo, inn_root())[0]
        self.assertPoint(lamp_doodad.position, (MID - 2000.0, MID - 1005.0, 11.0))
        self.assertMatrix(lamp_doodad.rotation, IDENTITY)
        self.assertEqual(lamp_doodad.scale, 0.5)
        self.assertEqual(lamp_doodad.flags, FLAG_WMO_DOODAD)
        self.assertEqual(lamp_doodad.unique_id, (21 << 32) | 0)
        self.assertPoint(lw.transform_point(lamp_doodad, (2.0, 0.0, 0.0)), (MID - 1999.0, MID - 1005.0, 11.0))

    def test_doodad_rotation_applies_inside_the_wmo_rotation(self):
        wmo = lw.placement_from_modf(modf((0.0, 0.0, 0.0), (0.0, 90.0, 0.0)))
        tilted = WmoRoot([DoodadSet("Set_$DefaultGlobal", 0, 1)],
                         [WmoDoodad("World\\Lamp.m2", (0.0, 0.0, 0.0), (math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)),
                                    1.0)])
        doodad = lw.wmo_doodad_placements(wmo, tilted)[0]
        self.assertPoint(lw.transform_point(doodad, (0.0, 1.0, 0.0)), (0.0, 0.0, 1.0))
        self.assertPoint(lw.transform_point(doodad, (1.0, 0.0, 0.0)), (0.0, -1.0, 0.0))

    def test_global_wmo_at_the_origin_is_anchored_to_the_map_centre(self):
        wmo = lw.placement_from_modf(modf((0.0, 5.0, 0.0)), FLAG_GLOBAL_WMO)
        self.assertPoint(wmo.position, (0.0, 0.0, 5.0))
        doodad = lw.wmo_doodad_placements(wmo, WmoRoot([DoodadSet("Set_$DefaultGlobal", 0, 1)],
                                                       [WmoDoodad("World\\Lamp.m2", (1.0, 2.0, 3.0),
                                                                  (0.0, 0.0, 0.0, 1.0), 1.0)]))[0]
        self.assertPoint(doodad.position, (-1.0, -2.0, 8.0))
        self.assertEqual(doodad.flags, FLAG_GLOBAL_WMO | FLAG_WMO_DOODAD)

    def test_default_set_plus_the_chosen_set(self):
        wmo = lw.placement_from_modf(modf((0.0, 0.0, 1.0)))
        chosen = [placement.model for placement in lw.wmo_doodad_placements(wmo, inn_root(), 2)]
        self.assertEqual(chosen, ["World\\Lamp.m2", "World\\Chair.m2", "World\\Candle.m2"])
        default = [placement.model for placement in lw.wmo_doodad_placements(wmo, inn_root(), 0)]
        self.assertEqual(default, ["World\\Lamp.m2", "World\\Chair.m2"])
        unknown = [placement.model for placement in lw.wmo_doodad_placements(wmo, inn_root(), 9)]
        self.assertEqual(unknown, default)
        party = lw.wmo_doodad_placements(wmo, inn_root(), 1)
        self.assertEqual([placement.unique_id & 0xFFFFFFFF for placement in party], [0, 1, 2])


class Lamps(Geometry):
    def test_world_lamps_scale_colour_and_reach(self):
        placement = lw.placement_from_mddf(mddf((100.0, 50.0, 200.0), scale=2048))
        verdict = ModelVerdict(ROUTE_NAME, [ModelLamp((0.0, 0.0, 1.0), (1.0, 0.5, 0.25), 2.0, 10.0, KIND_LAMP,
                                                      ROUTE_NAME, FLAG_BOUNDS_FALLBACK)])
        lamp = lw.world_lamps(placement, verdict, 42)[0]
        self.assertEqual((lamp.map_id, lamp.kind, lamp.route, lamp.flags, lamp.model),
                         (42, KIND_LAMP, ROUTE_NAME, FLAG_BOUNDS_FALLBACK, "World\\Lamp.m2"))
        self.assertPoint(lamp.position, (MID - 200.0, MID - 100.0, 52.0))
        self.assertEqual(lamp.color, (4.0, 2.0, 1.0))
        self.assertEqual(lamp.reach, 20.0)
        self.assertEqual(lw.world_lamps(placement, ModelVerdict(None), 42), [])

    def test_a_placement_at_no_finite_position_gives_no_lamp_and_the_dedupe_survives(self):
        verdict = ModelVerdict(ROUTE_FLAME, [ModelLamp((0.0, 0.0, 1.0), (1.0, 0.5, 0.25), 2.0, 10.0, KIND_TORCH,
                                                       ROUTE_FLAME)])
        lamps = lw.world_lamps(lw.placement_from_mddf(mddf((math.nan, 50.0, 200.0))), verdict, 42)
        self.assertEqual(lamps, [])
        self.assertEqual(lw.dedupe_lamps(lamps), [])

    def test_dedupe_keeps_the_brightest_within_half_a_yard(self):
        def lamp(position, brightness, kind=KIND_TORCH, route=ROUTE_FLAME):
            return Lamp(1, position, (brightness, brightness * 0.5, 0.0), 8.0, kind, route, 0)
        dim = lamp((0.0, 0.0, 0.0), 1.0)
        bright = lamp((0.4, 0.0, 0.0), 2.0)
        apart = lamp((1.0, 0.0, 0.0), 1.5)
        other_kind = lamp((0.0, 0.0, 0.0), 1.0, kind=KIND_CANDLE)
        other_route = lamp((0.0, 0.0, 0.0), 1.0, route=ROUTE_NAME)
        across_cells = [lamp((-10.1, 0.0, 0.0), 1.0), lamp((-9.9, 0.0, 0.0), 3.0)]
        kept = lw.dedupe_lamps([dim, bright, apart, other_kind, other_route] + across_cells)
        self.assertEqual(kept, [bright, apart, other_kind, other_route, across_cells[1]])
        self.assertEqual(lw.dedupe_lamps([dim, lamp((0.5, 0.0, 0.0), 0.5)]), [dim, lamp((0.5, 0.0, 0.0), 0.5)])


class FakeChain:
    def __init__(self, files, corrupt=()):
        self.files = {lw.model_key(name): versions for name, versions in files.items()}
        self.corrupt = {lw.model_key(name) for name in corrupt}
        self.read_calls = []
        self.prefix_calls = []
        self.version_calls = Counter()

    def stored(self, name):
        key = lw.model_key(name)
        if key in self.corrupt:
            raise MpqError("patch-A.MPQ: %s: corrupt sector" % name)
        return self.files.get(key, [])

    def version_reads(self, name):
        self.version_calls[lw.model_key(name)] += 1
        return [VersionRead(source, None, data) if isinstance(data, MpqError) else VersionRead(source, data, None)
                for source, data in self.stored(name)]

    def top(self, name):
        versions = self.stored(name)
        if versions and isinstance(versions[0][1], MpqError):
            raise versions[0][1]
        return versions[0][1] if versions else None

    def read(self, name):
        self.read_calls.append(lw.model_key(name))
        return self.top(name)

    def read_prefix(self, name, size):
        self.prefix_calls.append((lw.model_key(name), size))
        data = self.top(name)
        return data[:size] if data is not None else None


class FakeRules:
    def __init__(self):
        self.calls = []

    def __call__(self, top, stock):
        self.calls.append((top, stock))
        if top.lights:
            return ModelVerdict(ROUTE_AUTHORED, [ModelLamp(light.position, (1.0, 0.5, 0.25), 2.0, 10.0, KIND_LAMP,
                                                           ROUTE_AUTHORED) for light in top.lights])
        if stock is not None and stock.lights:
            return ModelVerdict(ROUTE_RESTORED, [ModelLamp(light.position, (1.0, 1.0, 1.0), 1.0, 6.0, KIND_LAMP,
                                                           ROUTE_RESTORED) for light in stock.lights])
        return ModelVerdict(None)


def textured(**spec):
    return fx.M2Spec(textures=[fx.TextureSpec("World\\Lamp.blp")], materials=[(0, 0)], texture_lookup=[0], **spec)


def lamp_m2(light_position=(0.0, 0.0, 1.0)):
    return fx.m2_bytes(textured(lights=[fx.LightSpec(position=light_position)]))


def dark_m2():
    return fx.m2_bytes(textured())


def skin(index_count):
    return fx.skin_bytes([fx.SubmeshSpec((0.0, 0.0, 1.0), index_count)], [fx.BatchSpec()])


def testland_files():
    names = ["World\\Lamp.mdx", "World\\Crate.m2", "World\\Ghost.m2"]
    inn = ["World\\wmo\\Inn.wmo"]
    west = fx.adt_bytes(names, inn, [fx.DoodadPlacement(0, 7, (100.0, 50.0, 200.0)),
                                     fx.DoodadPlacement(1, 1, (1.0, 2.0, 3.0)),
                                     fx.DoodadPlacement(2, 3, (4.0, 5.0, 6.0))],
                        [fx.WmoPlacement(0, 9, (1000.0, 10.0, 2000.0), doodad_set=1)])
    east = fx.adt_bytes(names, inn, [fx.DoodadPlacement(0, 7, (100.0, 50.0, 200.0)),
                                     fx.DoodadPlacement(0, 8, (300.0, 60.0, 400.0), (0.0, 90.0, 0.0), 2048),
                                     fx.DoodadPlacement(0, 9, (500.0, 70.0, 600.0))],
                        [fx.WmoPlacement(0, 9, (1000.0, 10.0, 2000.0), doodad_set=1)])
    inn_bytes = fx.wmo_root_bytes([("Set_$DefaultGlobal", 0, 1), ("Set_Party", 1, 1), ("Set_Night", 2, 1)],
                                  [fx.WmoDoodadSpec("World\\Lamp.m2", (5.0, 0.0, 1.0)),
                                   fx.WmoDoodadSpec("World\\Lamp.mdx", (0.0, 5.0, 1.0)),
                                   fx.WmoDoodadSpec("World\\Lamp.m2", (9.0, 9.0, 9.0))])
    return {
        "World\\Maps\\Testland\\Testland.wdt": [(STOCK, fx.wdt_bytes([(32, 32), (33, 32), (34, 32)]))],
        "World\\Maps\\Testland\\Testland_32_32.adt": [(STOCK, west)],
        "World\\Maps\\Testland\\Testland_33_32.adt": [(STOCK, east)],
        "World\\wmo\\Inn.wmo": [(STOCK, inn_bytes)],
        "World\\Lamp.m2": [(STOCK, lamp_m2())],
        "World\\Lamp00.skin": [(STOCK, skin(6))],
        "World\\Crate.m2": [(STOCK, dark_m2())],
    }


def isle_files(models):
    files = {"World\\Maps\\Isle\\Isle.wdt": [(STOCK, fx.wdt_bytes([(1, 1)]))],
             "World\\Maps\\Isle\\Isle_1_1.adt": [(STOCK, fx.adt_bytes(["World\\Torch.m2"], [],
                                                                     [fx.DoodadPlacement(0, 1, (0.0, 0.0, 0.0))], []))]}
    files.update(models)
    return files


class WalkMap(Geometry):
    def walk(self, files, map_id=42, directory="Testland", model_cache=None, census=None, corrupt=()):
        chain = FakeChain(files, corrupt)
        rules = FakeRules()
        cache = {} if model_cache is None else model_cache
        census = lw.Census() if census is None else census
        lamps = lw.walk_map(chain, map_id, directory, cache, census, classify=rules)
        return lamps, chain, rules, cache, census

    def test_places_each_unique_id_once_and_transforms_lamps(self):
        lamps, _, _, _, _ = self.walk(testland_files())
        positions = sorted(lamp.position for lamp in lamps)
        expected = sorted([(MID - 200.0, MID - 100.0, 51.0), (MID - 400.0, MID - 300.0, 62.0),
                           (MID - 600.0, MID - 500.0, 71.0), (MID - 2005.0, MID - 1000.0, 12.0),
                           (MID - 2000.0, MID - 1005.0, 12.0)])
        self.assertEqual(len(positions), len(expected))
        for actual, wanted in zip(positions, expected):
            self.assertPoint(actual, wanted)
        scaled = [lamp for lamp in lamps if abs(lamp.position[2] - 62.0) < 1e-3][0]
        self.assertEqual((scaled.color, scaled.reach, scaled.route), ((4.0, 2.0, 1.0), 20.0, ROUTE_AUTHORED))
        doodad_flags = sorted(lamp.flags for lamp in lamps)
        self.assertEqual(doodad_flags, [0, 0, 0, FLAG_WMO_DOODAD, FLAG_WMO_DOODAD])
        self.assertTrue(all(lamp.map_id == 42 for lamp in lamps))

    def test_placements_that_are_not_finite_are_counted_not_fatal(self):
        files = testland_files()
        names = ["World\\Lamp.m2"]
        inn = ["World\\wmo\\Inn.wmo"]
        broken = fx.adt_bytes(names, inn, [fx.DoodadPlacement(0, 70, (100.0, 50.0, 200.0), (0.0, math.inf, 0.0)),
                                           fx.DoodadPlacement(0, 71, (math.nan, 50.0, 200.0)),
                                           fx.DoodadPlacement(0, 72, (700.0, 50.0, 800.0))],
                              [fx.WmoPlacement(0, 73, (1000.0, 10.0, 2000.0), (math.inf, 0.0, 0.0))])
        files["World\\Maps\\Testland\\Testland_34_32.adt"] = [(STOCK, broken)]
        lamps, _, _, _, census = self.walk(files)
        record = census.maps[42]
        self.assertEqual(record.errors, {lw.NOT_FINITE: 3})
        self.assertEqual((record.tiles, record.placements, record.lamps), (3, 8, 6))
        self.assertTrue(any(abs(lamp.position[0] - (MID - 800.0)) < 1e-3 for lamp in lamps))

    def test_census_counts_tiles_placements_and_missing_files(self):
        _, _, _, _, census = self.walk(testland_files())
        record = census.maps[42]
        self.assertEqual((record.directory, record.tiles, record.placements, record.wmo_placements, record.lamps),
                         ("Testland", 3, 7, 1, 5))
        self.assertEqual(record.routes, {ROUTE_AUTHORED: 5})
        self.assertEqual(record.missing, {lw.FILE_ADT: 1, lw.FILE_M2: 1})
        lamp = census.models["WORLD\\LAMP.M2"]
        self.assertEqual((lamp.placements, lamp.archives, lamp.version_lights, lamp.top_lights, lamp.route),
                         ({42: 5}, ["common.MPQ"], [1], 1, ROUTE_AUTHORED))
        self.assertIn("missing file", census.models["WORLD\\GHOST.M2"].notes)
        self.assertEqual([model.path for model in census.notable_models()], ["WORLD\\LAMP.M2"])

    def test_models_are_evaluated_once_and_adts_read_as_prefixes(self):
        files = testland_files()
        _, chain, rules, cache, _ = self.walk(files)
        self.assertEqual(sorted(top.path for top, _ in rules.calls), ["WORLD\\CRATE.M2", "WORLD\\LAMP.M2"])
        self.assertEqual(chain.version_calls["WORLD\\LAMP.M2"], 1)
        self.assertEqual(chain.version_calls["WORLD\\LAMP00.SKIN"], 1)
        self.assertEqual(set(cache), {"WORLD\\LAMP.M2", "WORLD\\CRATE.M2", "WORLD\\GHOST.M2"})
        self.assertEqual(cache["WORLD\\GHOST.M2"].route, None)
        self.assertFalse([name for name in chain.read_calls if name.endswith(".ADT")])
        self.assertEqual(chain.read_calls.count("WORLD\\WMO\\INN.WMO"), 1)
        west = files["World\\Maps\\Testland\\Testland_32_32.adt"][0][1]
        sizes = [size for name, size in chain.prefix_calls if name.endswith("_32_32.ADT")]
        self.assertEqual(sizes[0], 0x54)
        self.assertEqual(sizes[-1], west.index(b"KNCM"))
        lamp_model = [top for top, _ in rules.calls if top.path == "WORLD\\LAMP.M2"][0]
        self.assertEqual(lamp_model.batches[0].index_count, 6)

    def test_shared_cache_is_reused_on_the_next_map(self):
        files = testland_files()
        cache = {}
        census = lw.Census()
        self.walk(files, model_cache=cache, census=census)
        files["World\\Maps\\Copy\\Copy.wdt"] = [(STOCK, fx.wdt_bytes([(32, 32)]))]
        files["World\\Maps\\Copy\\Copy_32_32.adt"] = files["World\\Maps\\Testland\\Testland_32_32.adt"]
        lamps, _, rules, _, _ = self.walk(files, map_id=43, directory="Copy", model_cache=cache, census=census)
        self.assertEqual(rules.calls, [])
        self.assertEqual(len(lamps), 3)
        self.assertEqual(census.models["WORLD\\LAMP.M2"].placements, {42: 5, 43: 3})
        self.assertEqual(census.maps[43].missing, {lw.FILE_M2: 1})

    def test_global_wmo_map(self):
        crypt = fx.wmo_root_bytes([("Set_$DefaultGlobal", 0, 1)], [fx.WmoDoodadSpec("World\\Lamp.m2", (1.0, 2.0, 3.0))])
        files = {"World\\Maps\\Crypt\\Crypt.wdt": [(STOCK, fx.wdt_bytes(
                     [], "World\\wmo\\Crypt.wmo", fx.WmoPlacement(0, 5, (0.0, 5.0, 0.0))))],
                 "World\\wmo\\Crypt.wmo": [(STOCK, crypt)],
                 "World\\Lamp.m2": [(STOCK, lamp_m2())]}
        lamps, _, _, _, census = self.walk(files, map_id=600, directory="Crypt")
        self.assertEqual(len(lamps), 1)
        self.assertPoint(lamps[0].position, (-1.0, -2.0, 9.0))
        self.assertEqual(lamps[0].flags, FLAG_GLOBAL_WMO | FLAG_WMO_DOODAD)
        self.assertEqual((census.maps[600].tiles, census.maps[600].wmo_placements), (0, 1))

    def test_unreadable_archive_data_is_counted_not_fatal(self):
        corrupt = ["World\\Maps\\Testland\\Testland_33_32.adt", "World\\Crate.m2", "World\\Lamp00.skin"]
        lamps, _, _, cache, census = self.walk(testland_files(), corrupt=corrupt)
        self.assertEqual(len(lamps), 3)
        self.assertEqual(census.maps[42].errors, {lw.FILE_ADT: 1})
        self.assertTrue(cache["WORLD\\CRATE.M2"].notes[0].startswith("unreadable: patch-A.MPQ"))
        self.assertTrue(any(note.startswith("skin unreadable") for note in cache["WORLD\\LAMP.M2"].notes))
        _, _, _, _, broken = self.walk(testland_files(), corrupt=["World\\Maps\\Testland\\Testland.wdt"])
        self.assertEqual(broken.maps[42].errors, {lw.FILE_WDT: 1})

    def test_an_unreadable_lower_version_is_noted_while_the_top_is_judged(self):
        files = isle_files({
            "World\\Torch.m2": [(CUSTOM, lamp_m2()), (PATCH, MpqError("patch-3.MPQ: WORLD\\TORCH.M2: mask 0x12")),
                                 (STOCK, dark_m2())],
            "World\\Torch00.skin": [(CUSTOM, skin(9)), (STOCK, MpqError("common.MPQ: WORLD\\TORCH00.SKIN: bad"))]})
        lamps, _, rules, cache, census = self.walk(files, map_id=1, directory="Isle")
        (top_model, stock_model), = rules.calls
        self.assertEqual((len(top_model.lights), top_model.batches[0].index_count), (1, 9))
        self.assertEqual((len(stock_model.lights), stock_model.batches), (0, []))
        self.assertEqual([lamp.route for lamp in lamps], [ROUTE_AUTHORED])
        notes = cache["WORLD\\TORCH.M2"].notes
        self.assertIn("lower version unreadable: patch-3.MPQ: WORLD\\TORCH.M2: mask 0x12", notes)
        self.assertIn("skin unreadable: common.MPQ: WORLD\\TORCH00.SKIN: bad", notes)
        torch = census.models["WORLD\\TORCH.M2"]
        self.assertEqual((torch.archives, torch.version_lights, torch.route),
                         (["patch-A.MPQ", "patch-3.MPQ", "common.MPQ"], [1, None, 0], ROUTE_AUTHORED))

    def test_an_unreadable_top_version_leaves_the_model_unjudged(self):
        files = isle_files({"World\\Torch.m2": [(CUSTOM, MpqError("patch-A.MPQ: WORLD\\TORCH.M2: bad")),
                                                 (STOCK, lamp_m2())]})
        lamps, _, rules, cache, _ = self.walk(files, map_id=1, directory="Isle")
        self.assertEqual((lamps, rules.calls), ([], []))
        self.assertEqual(cache["WORLD\\TORCH.M2"].notes, ["unreadable: patch-A.MPQ: WORLD\\TORCH.M2: bad"])

    def test_missing_wdt_is_counted(self):
        lamps, _, _, _, census = self.walk({}, map_id=7, directory="Nowhere")
        self.assertEqual(lamps, [])
        self.assertEqual(census.maps[7].missing, {lw.FILE_WDT: 1})

    def test_stock_is_the_highest_priority_stock_version_that_differs(self):
        top = dark_m2()
        files = {"World\\Maps\\Isle\\Isle.wdt": [(STOCK, fx.wdt_bytes([(1, 1)]))],
                 "World\\Maps\\Isle\\Isle_1_1.adt": [(STOCK, fx.adt_bytes(["World\\Torch.m2"], [],
                                                                         [fx.DoodadPlacement(0, 1, (0.0, 0.0, 0.0))],
                                                                         []))],
                 "World\\Torch.m2": [(CUSTOM, top), (PATCH, top), (STOCK, lamp_m2((0.0, 0.0, 2.0)))],
                 "World\\Torch00.skin": [(CUSTOM, skin(9)), (STOCK, skin(3))]}
        lamps, _, rules, _, census = self.walk(files, map_id=1, directory="Isle")
        (top_model, stock_model), = rules.calls
        self.assertEqual((len(top_model.lights), len(stock_model.lights)), (0, 1))
        self.assertEqual((top_model.batches[0].index_count, stock_model.batches[0].index_count), (9, 3))
        self.assertEqual([lamp.route for lamp in lamps], [ROUTE_RESTORED])
        torch = census.models["WORLD\\TORCH.M2"]
        self.assertEqual((torch.archives, torch.version_lights, torch.top_lights, torch.stock_lights),
                         (["patch-A.MPQ", "patch-3.MPQ", "common.MPQ"], [0, 0, 1], 0, 1))

    def test_single_version_has_no_stock_and_parse_errors_are_notes(self):
        files = {"World\\Maps\\Isle\\Isle.wdt": [(STOCK, fx.wdt_bytes([(1, 1)]))],
                 "World\\Maps\\Isle\\Isle_1_1.adt": [(STOCK, fx.adt_bytes(
                     ["World\\Torch.m2", "World\\Broken.m2"], [],
                     [fx.DoodadPlacement(0, 1, (0.0, 0.0, 0.0)), fx.DoodadPlacement(1, 2, (0.0, 0.0, 0.0))], []))],
                 "World\\Torch.m2": [(CUSTOM, lamp_m2())],
                 "World\\Broken.m2": [(CUSTOM, b"MD20" + b"\x08\x01\0\0" + b"\0" * 16)]}
        lamps, _, rules, cache, _ = self.walk(files, map_id=1, directory="Isle")
        self.assertEqual([(top.path, stock) for top, stock in rules.calls], [("WORLD\\TORCH.M2", None)])
        self.assertIn("no skin", cache["WORLD\\TORCH.M2"].notes)
        self.assertIsNone(cache["WORLD\\BROKEN.M2"].route)
        self.assertTrue(cache["WORLD\\BROKEN.M2"].notes[0].startswith("parse error"))
        self.assertEqual(len(lamps), 1)

    def test_names(self):
        self.assertEqual(lw.adt_name("Azeroth", 32, 48), "World\\Maps\\Azeroth\\Azeroth_32_48.adt")
        self.assertEqual(lw.wdt_name("Azeroth"), "World\\Maps\\Azeroth\\Azeroth.wdt")
        self.assertEqual(lw.model_key("World/Generic/Lamp.m2"), "WORLD\\GENERIC\\LAMP.M2")
        self.assertEqual(lw.model_key("World/Généric/Lampß.m2"), "WORLD\\GéNéRIC\\LAMPß.M2")

    def test_placement_record(self):
        placement = Placement("X.m2", (0.0, 0.0, 0.0), IDENTITY, 1.0, 1)
        self.assertEqual(lw.transform_point(placement, (1.0, 2.0, 3.0)), (1.0, 2.0, 3.0))


if __name__ == "__main__":
    unittest.main()
