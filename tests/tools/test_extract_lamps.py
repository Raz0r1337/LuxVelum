import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import extract_lamps
import format_fixtures as fx
import lamp_world as lw
from lamp_formats import Mddf, Modf, parse_wmo_root
from lamp_types import (FLAG_WMO_DOODAD, KIND_BRAZIER, KIND_CANDLE, KIND_LAMP, KIND_TORCH, ROUTE_AUTHORED,
                        ROUTE_EMISSIVE, ROUTE_FLAME, ROUTE_NAME, ROUTE_RESTORED)
from lamp_writer import float32, read_lamp_data_file
from mpq_fixture import BLOCK_COUNT_FIELD, FixtureFile, build_mpq, with_header_words, write_marker_archive, write_mpq

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools")
DOODADS = "World\\Generic\\Human\\Passive Doodads\\"
TORCH = DOODADS + "Torches\\GenericTorch01.m2"
LANTERN = DOODADS + "Lanterns\\Lantern01.m2"
OLD_LANTERN = DOODADS + "Lanterns\\OldLantern01.m2"
BRAZIER = DOODADS + "Braziers\\Brazier01.m2"
LAMP_POST = DOODADS + "StreetLamps\\LampPost01.m2"
GLOW_ORB = DOODADS + "Lights\\GlowOrb01.m2"
CANDLE = DOODADS + "Candles\\Candle01.m2"
INN = "World\\wmo\\Azeroth\\Buildings\\Inn\\Inn.wmo"
WDT = "World\\Maps\\Azeroth\\Azeroth.wdt"
WEST_ADT = "World\\Maps\\Azeroth\\Azeroth_32_48.adt"
EAST_ADT = "World\\Maps\\Azeroth\\Azeroth_33_48.adt"
MAP_DBC = "DBFilesClient\\Map.dbc"

TORCH_LIGHT = (0.0, 0.0, 1.2)
LANTERN_LIGHT = (0.0, 0.0, 0.5)
BRAZIER_FLAME = (0.0, 0.0, 1.0)
LAMP_POST_GLOW = (0.0, 0.0, 3.5)
ORB_GLOW = (0.0, 0.0, 0.75)
CANDLE_FLAME = (0.0, 0.0, 0.3)

WEST_M2 = [TORCH, LANTERN, OLD_LANTERN, BRAZIER, LAMP_POST]
EAST_M2 = [BRAZIER, GLOW_ORB, TORCH.lower().replace("\\", "/")]
SHARED_BRAZIER = fx.DoodadPlacement(3, 500, (17150.0, 48.0, 25850.0))
WEST_DOODADS = [fx.DoodadPlacement(0, 101, (17100.0, 50.0, 25800.0), (0.0, 90.0, 0.0)),
                fx.DoodadPlacement(1, 102, (17110.0, 52.0, 25810.0), scale=2048),
                fx.DoodadPlacement(2, 103, (17120.0, 50.0, 25820.0)),
                SHARED_BRAZIER,
                fx.DoodadPlacement(4, 104, (17130.0, 50.0, 25830.0), (0.0, 45.0, 0.0))]
EAST_DOODADS = [fx.DoodadPlacement(0, 500, SHARED_BRAZIER.position),
                fx.DoodadPlacement(1, 105, (17600.0, 45.0, 25850.0)),
                fx.DoodadPlacement(2, 106, (17610.0, 45.0, 25860.0), (0.0, 180.0, 0.0))]
INN_PLACEMENT = fx.WmoPlacement(0, 900, (17200.0, 40.0, 25900.0), (0.0, 180.0, 0.0), doodad_set=0)
INN_DOODADS = [fx.WmoDoodadSpec(CANDLE, (2.0, 1.0, 1.0)), fx.WmoDoodadSpec(BRAZIER, (-3.0, 0.0, 0.0))]


def light(position, color, intensity, end):
    return fx.LightSpec(position=position, diffuse_color=color, diffuse_intensity=intensity, attenuation_end=end)


def stock_torch():
    return fx.m2_bytes(fx.M2Spec(bounds_min=(-0.25, -0.25, 0.0), bounds_max=(0.25, 0.25, 1.4),
                                 lights=[light(TORCH_LIGHT, (1.0, 0.5, 0.25), 1.0, 5.0)]))


def hd_torch():
    return fx.m2_bytes(fx.M2Spec(bounds_min=(-0.3, -0.3, 0.0), bounds_max=(0.3, 0.3, 1.5),
                                 textures=[fx.TextureSpec("World\\Generic\\Fire\\TorchFlame01.blp")],
                                 emitters=[fx.EmitterSpec(position=(0.0, 0.0, 1.3), texture=0)]))


def lantern():
    return fx.m2_bytes(fx.M2Spec(bounds_min=(-0.2, -0.2, 0.0), bounds_max=(0.2, 0.2, 0.8),
                                 lights=[light(LANTERN_LIGHT, (1.0, 0.8, 0.6), 1.5, 8.0)]))


def brazier():
    return fx.m2_bytes(fx.M2Spec(bounds_min=(-0.6, -0.6, 0.0), bounds_max=(0.6, 0.6, 1.2),
                                 textures=[fx.TextureSpec("World\\Generic\\Fire\\Fire01.blp")],
                                 emitters=[fx.EmitterSpec(position=BRAZIER_FLAME, texture=0)]))


def candle():
    return fx.m2_bytes(fx.M2Spec(bounds_min=(-0.05, -0.05, 0.0), bounds_max=(0.05, 0.05, 0.35),
                                 textures=[fx.TextureSpec("World\\Generic\\Fire\\CandleFlame.blp")],
                                 emitters=[fx.EmitterSpec(position=CANDLE_FLAME, texture=0, emission_rate=4.0,
                                                          colors=[(255.0, 200.0, 120.0)], alphas=[32767],
                                                          sizes=[(0.1, 0.1)])]))


def glowing(texture, blend, bounds_max):
    return fx.m2_bytes(fx.M2Spec(bounds_min=(-0.5, -0.5, 0.0), bounds_max=bounds_max,
                                 textures=[fx.TextureSpec(texture)], materials=[(1, blend)], texture_lookup=[0]))


def glow_skin(center, index_count):
    return fx.skin_bytes([fx.SubmeshSpec(center, index_count)], [fx.BatchSpec()])


def stock_files():
    inn = fx.wmo_root_bytes([("Set_$DefaultGlobal", 0, 1), ("Set_Night", 1, 1)], INN_DOODADS)
    west = fx.adt_bytes(WEST_M2, [INN], WEST_DOODADS, [INN_PLACEMENT])
    east = fx.adt_bytes(EAST_M2, [INN.upper()], EAST_DOODADS, [INN_PLACEMENT])
    files = {
        MAP_DBC: fx.map_dbc_bytes([(0, "Azeroth"), (1, "Kalimdor")]),
        WDT: fx.wdt_bytes([(32, 48), (33, 48)]),
        WEST_ADT: west, EAST_ADT: east, INN: inn,
        TORCH: stock_torch(), LANTERN: lantern(), OLD_LANTERN: lantern(), BRAZIER: brazier(), CANDLE: candle(),
        LAMP_POST: glowing(DOODADS + "StreetLamps\\LampGlow.blp", 2, (0.5, 0.5, 4.0)),
        LAMP_POST[:-3] + "00.skin": glow_skin(LAMP_POST_GLOW, 36),
        GLOW_ORB: glowing(DOODADS + "Lights\\OrbGlow.blp", 4, (0.5, 0.5, 1.0)),
        GLOW_ORB[:-3] + "00.skin": glow_skin(ORB_GLOW, 24),
    }
    return [FixtureFile(name, data, compression="zlib") for name, data in sorted(files.items())]


def build_data_folder(root):
    data = os.path.join(root, "Data")
    write_mpq(os.path.join(data, "common.MPQ"), stock_files(), version=2, listfile=True)
    write_mpq(os.path.join(data, "patch-A.MPQ"), [FixtureFile(TORCH, hd_torch(), compression="zlib"),
                                                  FixtureFile(OLD_LANTERN, delete_marker=True)])
    write_marker_archive(os.path.join(data, "enUS", "locale-enUS.MPQ"), "enUS/locale-enUS.MPQ")
    write_marker_archive(os.path.join(data, "backup.MPQ"), "backup.MPQ")
    return data


def write_bytes(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def add_damaged_archives(data):
    write_mpq(os.path.join(data, "patch-4.MPQ"), [FixtureFile(LANTERN, lantern(), forced_mask=0x01)])
    write_mpq(os.path.join(data, "patch-B.MPQ"), [FixtureFile(LANTERN, lantern(), compression="zlib")])
    cut = build_mpq([FixtureFile("marker.txt", b"patch-C", compression="zlib")])
    write_bytes(os.path.join(data, "patch-C.MPQ"), with_header_words(cut, BLOCK_COUNT_FIELD, 1001))
    write_bytes(os.path.join(data, "patch-Z.MPQ"), bytes(range(256)) * 16)


def mddf_of(placement):
    return Mddf(name_id=placement.name_id, unique_id=placement.unique_id, position=placement.position,
                rotation=placement.rotation, scale=placement.scale, flags=placement.flags)


def world_of(placement, point):
    return lw.transform_point(lw.placement_from_mddf(mddf_of(placement)), point)


def inn_candle_position():
    modf = Modf(name_id=0, unique_id=INN_PLACEMENT.unique_id, position=INN_PLACEMENT.position,
                rotation=INN_PLACEMENT.rotation, extents_min=(0.0, 0.0, 0.0), extents_max=(0.0, 0.0, 0.0),
                flags=0, doodad_set=0, name_set=0, name=INN)
    root = parse_wmo_root(fx.wmo_root_bytes([("Set_$DefaultGlobal", 0, 1), ("Set_Night", 1, 1)], INN_DOODADS))
    placements = lw.wmo_doodad_placements(lw.placement_from_modf(modf), root, 0)
    return lw.transform_point(placements[0], CANDLE_FLAME)


class ExtractLamps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        cls.data = build_data_folder(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def output_folder(self, name):
        folder = os.path.join(self.root, "out-" + name)
        os.makedirs(folder, exist_ok=True)
        return folder

    def run_tool(self, *arguments):
        out = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = extract_lamps.main(list(arguments), out)
        return code, out.getvalue(), errors.getvalue()

    def extract(self, name, *arguments):
        folder = self.output_folder(name)
        lamp_data = os.path.join(folder, "lampdata.bin")
        code, out, errors = self.run_tool("--data", self.data, "--out", lamp_data, *arguments)
        self.assertEqual(code, 0, out + errors)
        with open(os.path.join(folder, "lamps-census.txt"), encoding="utf-8") as handle:
            census = handle.read()
        return read_lamp_data_file(lamp_data), out, census

    def assertPoint(self, actual, expected):
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, float32(e), places=3)

    def lamps_by_route(self, lamps):
        routes = {}
        for lamp in lamps:
            routes.setdefault(lamp.route, []).append(lamp)
        return routes

    def test_every_route_comes_out_of_the_archives_in_world_space(self):
        written, out, _ = self.extract("all")
        self.assertEqual([record.map_id for record in written.maps], [0])
        self.assertEqual([source.path for source in written.sources],
                         ["common.MPQ", "enUS\\locale-enUS.MPQ", "patch-A.MPQ"])
        routes = self.lamps_by_route(written.lamps)
        self.assertEqual({route: len(lamps) for route, lamps in routes.items()},
                         {ROUTE_AUTHORED: 1, ROUTE_RESTORED: 2, ROUTE_FLAME: 2, ROUTE_NAME: 1, ROUTE_EMISSIVE: 1})

        lantern_lamp = routes[ROUTE_AUTHORED][0]
        self.assertPoint(lantern_lamp.position, world_of(WEST_DOODADS[1], LANTERN_LIGHT))
        self.assertPoint(lantern_lamp.color, (3.0, 2.4, 1.8))
        self.assertEqual((lantern_lamp.reach, lantern_lamp.kind), (16.0, KIND_LAMP))

        torches = sorted(routes[ROUTE_RESTORED], key=lambda lamp: lamp.position[1])
        expected = sorted([world_of(WEST_DOODADS[0], TORCH_LIGHT), world_of(EAST_DOODADS[2], TORCH_LIGHT)],
                          key=lambda point: point[1])
        for lamp, position in zip(torches, expected):
            self.assertPoint(lamp.position, position)
            self.assertPoint(lamp.color, (1.0, 0.5, 0.25))
            self.assertEqual((lamp.reach, lamp.kind, lamp.flags), (5.0, KIND_TORCH, 0))

        flames = {lamp.kind: lamp for lamp in routes[ROUTE_FLAME]}
        self.assertEqual(set(flames), {KIND_BRAZIER, KIND_CANDLE})
        self.assertPoint(flames[KIND_BRAZIER].position, world_of(SHARED_BRAZIER, BRAZIER_FLAME))
        self.assertEqual((flames[KIND_BRAZIER].reach, flames[KIND_BRAZIER].flags), (16.0, 0))
        self.assertPoint(flames[KIND_CANDLE].position, inn_candle_position())
        self.assertEqual((flames[KIND_CANDLE].reach, flames[KIND_CANDLE].flags), (6.0, FLAG_WMO_DOODAD))

        self.assertPoint(routes[ROUTE_NAME][0].position, world_of(WEST_DOODADS[4], LAMP_POST_GLOW))
        self.assertPoint(routes[ROUTE_NAME][0].color, (1.5, 1.5 * 0.72, 1.5 * 0.40))
        self.assertPoint(routes[ROUTE_EMISSIVE][0].position, world_of(EAST_DOODADS[1], ORB_GLOW))
        self.assertEqual(routes[ROUTE_EMISSIVE][0].kind, KIND_LAMP)

        self.assertIn("map 0 Azeroth: 2 tiles, 8 placements, 7 lamps (authored 1, restored 2, flame 2, name 1, "
                      "emissive 1)", out)
        self.assertIn("map 1 Kalimdor: 0 tiles, 0 placements, 0 lamps", out)
        self.assertIn("  custom  patch-A.MPQ", out)
        self.assertIn("ignored: backup.MPQ", out)
        self.assertIn("wrote 7 lamps on 1 map to ", out)

    def test_the_census_lists_archives_maps_and_lamp_models(self):
        _, _, census = self.extract("census")
        lines = census.splitlines()
        self.assertEqual(lines[0], "LuxVelum lamp census")
        self.assertIn("locale: enUS", lines)
        archives = lines.index("archives, lowest priority first:")
        self.assertEqual([line.split(",")[0] for line in lines[archives + 1:archives + 4]],
                         ["  stock   common.MPQ", "  stock   enUS/locale-enUS.MPQ", "  custom  patch-A.MPQ"])
        self.assertEqual(lines[archives + 4:archives + 6], ["ignored archives:", "  backup.MPQ"])
        self.assertIn("  map 0 Azeroth: 2 tiles, 8 placements, 7 lamps (authored 1, restored 2, flame 2, name 1, "
                      "emissive 1)", lines)
        self.assertIn("    1 WMO placement; missing: m2 1", lines)
        self.assertIn("    0 WMO placements; missing: wdt 1", lines)
        self.assertIn("all maps: 7 lamps (authored 1, restored 2, flame 2, name 1, emissive 1)", lines)
        self.assertTrue(any(line.startswith("written to ") and line.endswith(
            ": 7 lamps; 0 brought into range, 0 dropped as unstorable") for line in lines))

        models = lines[lines.index("models that look like lamps or carry light blocks, most placed first: 7") + 1:]
        paths = [line.strip() for line in models if line.startswith("  ") and not line.startswith("    ")]
        self.assertEqual(paths[0], lw.model_key(TORCH))
        self.assertEqual(set(paths[1:]), {lw.model_key(name) for name in
                                          (LANTERN, OLD_LANTERN, BRAZIER, LAMP_POST, GLOW_ORB, CANDLE)})
        self.assertEqual(models[1:6], ["    placements: 2 (map 0: 2)",
                                       "    versions: patch-A.MPQ (custom): 0 lights; common.MPQ (stock): 1 light",
                                       "    lights: top 0, stock 1", "    route: restored",
                                       "    notes: no skin; stock: no skin"])
        old = models.index("  " + lw.model_key(OLD_LANTERN))
        self.assertEqual(models[old + 1:old + 6], ["    placements: 1 (map 0: 1)", "    versions: none",
                                                   "    lights: top 0, stock 0", "    route: none",
                                                   "    notes: missing file"])
        self.assertNotIn(lw.model_key(INN), census)

    def test_a_shared_placement_is_placed_once(self):
        _, _, census = self.extract("shared")
        lines = census.splitlines()
        brazier = lines.index("  " + lw.model_key(BRAZIER))
        self.assertEqual(lines[brazier + 1], "    placements: 1 (map 0: 1)")
        candle_entry = lines.index("  " + lw.model_key(CANDLE))
        self.assertEqual(lines[candle_entry + 1], "    placements: 1 (map 0: 1)")

    def test_an_archive_order_file_replaces_the_client_order(self):
        folder = self.output_folder("order")
        order = os.path.join(folder, "order.txt")
        with open(order, "w", encoding="utf-8") as handle:
            handle.write("# only the stock archives\ncommon.MPQ\n\nenUS\\locale-enUS.MPQ\n")
        written, out, census = self.extract("order", "--archives", order)
        routes = self.lamps_by_route(written.lamps)
        self.assertEqual({route: len(lamps) for route, lamps in routes.items()},
                         {ROUTE_AUTHORED: 4, ROUTE_FLAME: 2, ROUTE_NAME: 1, ROUTE_EMISSIVE: 1})
        self.assertIn("ignored: backup.MPQ, patch-A.MPQ", out)
        self.assertIn("ignored archives:\n  backup.MPQ\n  patch-A.MPQ\n", census)

    def test_maps_can_be_chosen(self):
        written, out, _ = self.extract("maps", "--maps", "1,999")
        self.assertEqual((written.maps, written.lamps), ([], []))
        self.assertIn("map 999 is not in DBFilesClient\\Map.dbc and is skipped", out)
        self.assertNotIn("map 0 Azeroth", out)

    def test_by_default_the_data_goes_to_data_luxvelum(self):
        data = os.path.join(self.root, "default", "Data")
        shutil.copytree(self.data, data)
        code, out, errors = self.run_tool("--data", data, "--maps", "0")
        self.assertEqual(code, 0, out + errors)
        self.assertEqual(len(read_lamp_data_file(os.path.join(data, "LuxVelum", "lampdata.bin")).lamps), 7)
        self.assertTrue(os.path.isfile(os.path.join(data, "LuxVelum", "lamps-census.txt")))

    def test_model_mode_describes_every_version_and_writes_nothing(self):
        folder = self.output_folder("model")
        code, out, errors = self.run_tool("--data", self.data, "--out", os.path.join(folder, "lampdata.bin"),
                                          "--model", TORCH.lower().replace("\\", "/")[:-3] + ".mdx", OLD_LANTERN)
        self.assertEqual(code, 0, out + errors)
        self.assertEqual(os.listdir(folder), [])
        torch_path = TORCH.lower()
        self.assertIn("\n" + torch_path + "\n", out)
        self.assertIn("  version 1 of 2: patch-A.MPQ (custom), ", out)
        self.assertIn("  version 2 of 2: common.MPQ (stock), ", out)
        self.assertIn("    lights: 0\n", out)
        self.assertIn("    lights: 1\n      light 0: point, bone -1, at (0.00, 0.00, 1.20), colour (1.00, 0.50, 0.25) "
                      "x 1.00, attenuation 1.00 to 5.00, visible, emits\n", out)
        self.assertIn("emitter 0: texture World\\Generic\\Fire\\TorchFlame01.blp, blend 4, peak rate 20.00, peak size "
                      "0.50, at (0.00, 0.00, 1.30), flame of strength 1.06", out)
        self.assertIn("  verdict: restored, 1 lamp\n    lamp 0: restored torch at (0.00, 0.00, 1.20), colour (1.00, "
                      "0.50, 0.25) x 1.00, reach 5.0 yd, flags none\n", out)
        self.assertIn(OLD_LANTERN + "\n  in no archive: missing file\n  verdict: none, 0 lamps\n  notes: missing file",
                      out)

    def test_damaged_archives_and_versions_are_noted_not_fatal(self):
        data = os.path.join(self.root, "damaged", "Data")
        shutil.copytree(self.data, data)
        add_damaged_archives(data)
        folder = self.output_folder("damaged")
        lamp_data = os.path.join(folder, "lampdata.bin")
        code, out, errors = self.run_tool("--data", data, "--out", lamp_data)
        self.assertEqual(code, 0, out + errors)
        self.assertIn("  custom  patch-C.MPQ\n    the block table is cut to 1 of 1001 entries by the end of the "
                      "file\n", out)
        self.assertIn("unreadable, skipped: patch-Z.MPQ (no MPQ header found)", out)
        written = read_lamp_data_file(lamp_data)
        self.assertEqual([source.path for source in written.sources],
                         ["common.MPQ", "enUS\\locale-enUS.MPQ", "patch-4.MPQ", "patch-A.MPQ", "patch-B.MPQ",
                          "patch-C.MPQ"])
        self.assertEqual(len(written.lamps), 7)
        self.assertEqual(len(self.lamps_by_route(written.lamps)[ROUTE_AUTHORED]), 1)
        with open(os.path.join(folder, "lamps-census.txt"), encoding="utf-8") as handle:
            census = handle.read()
        self.assertIn("unreadable archives, skipped:\n  patch-Z.MPQ, 4 096 bytes: no MPQ header found\n", census)
        self.assertIn("    the block table is cut to 1 of 1001 entries by the end of the file\n", census)
        self.assertIn("    versions: patch-B.MPQ (custom): 1 light; patch-4.MPQ (custom): unreadable; common.MPQ "
                      "(stock): 1 light\n", census)
        self.assertIn("lower version unreadable: ", census)
        code, out, errors = self.run_tool("--data", data, "--model", LANTERN)
        self.assertEqual(code, 0, out + errors)
        self.assertIn("  version 2 of 3: patch-4.MPQ (custom), unreadable\n    unreadable: ", out)
        self.assertIn("  verdict: authored, 1 lamp\n", out)

    def test_usage_errors_exit_with_2(self):
        missing = os.path.join(self.root, "no-such-folder")
        bad_order = os.path.join(self.output_folder("bad-order"), "order.txt")
        with open(bad_order, "w", encoding="utf-8") as handle:
            handle.write("common.MPQ\npatch-Z.MPQ\n")
        for arguments in ([], ["--data", self.data, "--maps", "zero"], ["--data", self.data, "--maps", "-1"],
                          ["--data", missing], ["--data", self.data, "--archives", bad_order],
                          ["--data", self.data, "--archives", bad_order + ".missing"], ["--data", self.data, "--x"]):
            with self.subTest(arguments=arguments):
                code, _, errors = self.run_tool(*arguments)
                self.assertEqual(code, 2)
                self.assertIn("error", errors)

    def test_no_archive_or_no_map_table_exits_with_1(self):
        empty = os.path.join(self.root, "empty", "Data")
        os.makedirs(empty)
        code, out, _ = self.run_tool("--data", empty)
        self.assertEqual(code, 1)
        self.assertIn("no MPQ archive found in", out)
        junk = os.path.join(self.root, "junk", "Data")
        os.makedirs(junk)
        write_bytes(os.path.join(junk, "common.MPQ"), bytes(4096))
        code, out, _ = self.run_tool("--data", junk)
        self.assertEqual(code, 1)
        self.assertIn("unreadable, skipped: common.MPQ (no MPQ header found)", out)
        self.assertIn("could be opened", out)
        without_maps = os.path.join(self.root, "without-maps", "Data")
        write_marker_archive(os.path.join(without_maps, "common.MPQ"), "common.MPQ")
        code, out, _ = self.run_tool("--data", without_maps, "--out", os.path.join(without_maps, "lampdata.bin"))
        self.assertEqual(code, 1)
        self.assertIn("no DBFilesClient\\Map.dbc in any archive", out)
        self.assertFalse(os.path.exists(os.path.join(without_maps, "lampdata.bin")))

    def test_the_script_runs_from_the_command_line(self):
        folder = self.output_folder("script")
        lamp_data = os.path.join(folder, "lampdata.bin")
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        environment.pop("PYTHONPATH", None)
        finished = subprocess.run([sys.executable, os.path.join(TOOLS, "extract_lamps.py"), "--data", self.data,
                                   "--out", lamp_data, "--census", os.path.join(folder, "census.txt")],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                                  universal_newlines=True, timeout=120)
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertIn("done in ", finished.stdout)
        self.assertEqual(len(read_lamp_data_file(lamp_data).lamps), 7)
        self.assertTrue(os.path.isfile(os.path.join(folder, "census.txt")))


if __name__ == "__main__":
    unittest.main()
