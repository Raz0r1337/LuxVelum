import contextlib
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

import format_fixtures as fx
import inspect_models_near as probe
import lamp_world as lw
from model_materials import parse_m2_materials, parse_world_map_area_dbc
from mpq_fixture import FixtureFile, write_mpq

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools")
ASHENVALE_DOODADS = "World\\Kalimdor\\Ashenvale\\PassiveDoodads\\"
STONE = ASHENVALE_DOODADS + "Runestones\\AshenvaleRunestone01.m2"
LAMP_TREE = ASHENVALE_DOODADS + "Trees\\AshenvaleLampTree01.m2"
BASIN = ASHENVALE_DOODADS + "Basins\\MoonwellBasin01.m2"
GHOST = ASHENVALE_DOODADS + "Missing\\Ghost01.m2"
BROKEN = ASHENVALE_DOODADS + "Broken\\Broken01.m2"
TENT = ASHENVALE_DOODADS + "Tents\\NightElfTent01.m2"
LANTERN = "World\\Generic\\NightElf\\Passive Doodads\\Lanterns\\NE_Lantern01.m2"
TORCH = "World\\Generic\\NightElf\\Passive Doodads\\Torches\\NE_Torch01.m2"
SHRINE = "World\\wmo\\Kalimdor\\Ashenvale\\Shrine\\Shrine.wmo"
FAR_HUT = "World\\wmo\\Kalimdor\\Ashenvale\\Hut\\Hut.wmo"
WDT = "World\\Maps\\Kalimdor\\Kalimdor.wdt"
NORTH_ADT = "World\\Maps\\Kalimdor\\Kalimdor_31_25.adt"
SOUTH_ADT = "World\\Maps\\Kalimdor\\Kalimdor_31_26.adt"
MAP_DBC = "DBFilesClient\\Map.dbc"
WORLD_MAP_AREA_DBC = "DBFilesClient\\WorldMapArea.dbc"

ASHENVALE = (43, 1, 331, "Ashenvale", 1699.9999, -4066.6665, 4672.9165, 829.16663)
DARKSHORE = (42, 1, 148, "Darkshore", 2941.6665, -3608.3333, 8333.333, 4266.6665)
ELWYNN = (37, 0, 12, "Elwynn", 1535.4166, -1935.4166, -7939.5835, -10254.166)
MAESTRAS_POST = (26.4, 38.5)
SECOND_SIGHTING = (20.4, 42.7)
GROUND = 100.0
FIXED16_HALF = 16384
FIXED16_QUARTER = 8191
FIXED16_ONE = 32767
FIXED16_JUST_BELOW_ONE = 32766


def float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def zone_world(percent):
    left, right, top, bottom = (float32(value) for value in ASHENVALE[4:])
    return top + percent[1] / 100.0 * (bottom - top), left + percent[0] / 100.0 * (right - left)


POINT_A = zone_world(MAESTRAS_POST)
POINT_B = zone_world(SECOND_SIGHTING)


def internal(point, dx, dy, z=GROUND):
    return (lw.MAP_ORIGIN - (point[1] + dy), z, lw.MAP_ORIGIN - (point[0] + dx))


def skin_name(model):
    return model[:-3] + "00.skin"


def static_track(*keys):
    return fx.KeyTrackSpec([[(key,) for key in keys]])


def hd_stone():
    return fx.m2_bytes(fx.M2Spec(
        bounds_min=(-1.5, -1.0, 0.0), bounds_max=(1.5, 1.0, 3.0),
        sequences=[fx.SequenceSpec(), fx.SequenceSpec(flags=0, animation=1)],
        textures=[fx.TextureSpec(ASHENVALE_DOODADS + "Runestones\\Runestone_HD.blp"), fx.TextureSpec(texture_type=2)],
        materials=[(0x4, 1), (0x0, 2)], texture_lookup=[0, 1], texture_unit_lookup=[0, -1],
        colors=[fx.ColorSpec(rgb=fx.KeyTrackSpec([[(0.25, 0.25, 0.3)]]), alpha=static_track(FIXED16_HALF))],
        texture_weights=[static_track(FIXED16_ONE),
                         fx.KeyTrackSpec([[(FIXED16_QUARTER,), (FIXED16_ONE,)], [(0,)]], detached=(1,))],
        transparency_lookup=[0, 1]))


def hd_stone_skin():
    return fx.skin_bytes([fx.SubmeshSpec(index_count=900), fx.SubmeshSpec(index_count=120)],
                         [fx.BatchSpec(submesh=0, material=0, texture_count=2, color=0, shader=0x11, flags=0x10),
                          fx.BatchSpec(submesh=1, material=1, texture_weight_combo=1, priority=1, layer=1)])


def stock_stone():
    return fx.m2_bytes(fx.M2Spec(textures=[fx.TextureSpec(ASHENVALE_DOODADS + "Runestones\\Runestone.blp")],
                                 materials=[(0, 0)], texture_lookup=[0], texture_unit_lookup=[0],
                                 texture_weights=[static_track(FIXED16_ONE)], transparency_lookup=[0]))


def single_batch_skin(index_count=36):
    return fx.skin_bytes([fx.SubmeshSpec(index_count=index_count)], [fx.BatchSpec()])


def lamp_tree():
    return fx.m2_bytes(fx.M2Spec(
        textures=[fx.TextureSpec(ASHENVALE_DOODADS + "Trees\\LampTreeBark.blp"),
                  fx.TextureSpec(ASHENVALE_DOODADS + "Trees\\LampTreeGlow.blp")],
        materials=[(0, 0), (0x3, 4)], texture_lookup=[0, 1], texture_unit_lookup=[0],
        colors=[fx.ColorSpec(rgb=fx.KeyTrackSpec([[(0.2, 0.4, 1.0)], [(0.4, 0.6, 1.0)]]),
                             alpha=fx.KeyTrackSpec([[(FIXED16_ONE,)]], global_sequence=0))],
        texture_weights=[static_track(FIXED16_ONE)], transparency_lookup=[0],
        sequences=[fx.SequenceSpec(), fx.SequenceSpec(animation=1)]))


def lamp_tree_skin():
    return fx.skin_bytes([fx.SubmeshSpec(index_count=600), fx.SubmeshSpec(index_count=48)],
                         [fx.BatchSpec(submesh=0, material=0),
                          fx.BatchSpec(submesh=1, material=1, texture_combo=1, color=0)])


def basin():
    return fx.m2_bytes(fx.M2Spec(
        global_flags=0x8, combiner_combos=[0x11, 0x5],
        textures=[fx.TextureSpec(ASHENVALE_DOODADS + "Basins\\BasinFlame.blp")],
        materials=[(0, 7), (0, 5), (0, 6), (0, 0)], texture_lookup=[0], texture_unit_lookup=[0],
        texture_weights=[static_track(FIXED16_ONE), static_track(FIXED16_JUST_BELOW_ONE)],
        transparency_lookup=[0, 1]))


def basin_skin():
    return fx.skin_bytes([fx.SubmeshSpec(index_count=24)],
                         [fx.BatchSpec(material=0, shader=1), fx.BatchSpec(material=1), fx.BatchSpec(material=2),
                          fx.BatchSpec(material=3, texture_weight_combo=1)])


def simple_model(texture):
    return fx.m2_bytes(fx.M2Spec(textures=[fx.TextureSpec(texture)], materials=[(0, 1)], texture_lookup=[0],
                                 texture_unit_lookup=[0], texture_weights=[static_track(FIXED16_ONE)],
                                 transparency_lookup=[0]))


SHRINE_DOODADS = [fx.WmoDoodadSpec(STONE, (2.0, 0.0, 0.0)), fx.WmoDoodadSpec(LANTERN, (0.0, 3.0, 1.0)),
                  fx.WmoDoodadSpec(TORCH, (0.0, -3.0, 0.0))]
SHRINE_SETS = [("Set_$DefaultGlobal", 0, 1), ("Set_Night", 1, 1), ("Set_Day", 2, 1)]


def shrine():
    return fx.wmo_root_bytes(
        SHRINE_SETS, SHRINE_DOODADS, groups=3, flags=0x1,
        materials=[fx.WmoMaterialSpec(flags=0x8, texture="Shrine_Wall.blp", diffuse_color=0xFF404040),
                   fx.WmoMaterialSpec(flags=0x3, shader=6, blend=1, texture="Shrine_Glow.blp",
                                      second_texture="Shrine_Glow2.blp", sidn_color=0xFF6080FF)],
        fogs=[fx.WmoFogSpec(color=0xFF203040)])


def shrine_placement():
    return fx.WmoPlacement(0, 900, internal(POINT_A, -10.0, 0.0), doodad_set=1,
                           extents_min=internal(POINT_A, -2.0, 8.0, 90.0),
                           extents_max=internal(POINT_A, -18.0, -8.0, 110.0))


def far_hut_placement():
    return fx.WmoPlacement(1, 901, internal(POINT_A, 200.0, 0.0), extents_min=internal(POINT_A, 205.0, 5.0, 90.0),
                           extents_max=internal(POINT_A, 195.0, -5.0, 110.0))


SOUTH_M2 = [STONE, LAMP_TREE, GHOST, TENT, BROKEN]
SOUTH_DOODADS = [fx.DoodadPlacement(0, 7001, internal(POINT_A, 3.0, 4.0), (0.0, 135.0, 0.0)),
                 fx.DoodadPlacement(1, 7003, internal(POINT_A, -6.0, 9.0), scale=2048),
                 fx.DoodadPlacement(2, 7004, internal(POINT_A, 0.0, -30.0)),
                 fx.DoodadPlacement(3, 7005, internal(POINT_A, 60.0, 0.0)),
                 fx.DoodadPlacement(4, 7006, internal(POINT_A, 0.0, 35.0)),
                 fx.DoodadPlacement(0, 7002, internal(POINT_B, 1.0, -1.0))]
NORTH_M2 = [STONE, BASIN[:-3] + ".mdx"]
NORTH_DOODADS = [SOUTH_DOODADS[0], fx.DoodadPlacement(1, 7007, internal(POINT_A, 20.0, -5.0))]
INSTANCE_MAP = 33
INSTANCE_WDT = "World\\Maps\\Shadowfang\\Shadowfang.wdt"


def stock_files():
    files = {
        MAP_DBC: fx.map_dbc_bytes([(0, "Azeroth"), (1, "Kalimdor"), (INSTANCE_MAP, "Shadowfang")]),
        WDT: fx.wdt_bytes([(31, 25), (31, 26)]),
        INSTANCE_WDT: fx.wdt_bytes([], SHRINE, fx.WmoPlacement(0, 77, (0.0, 0.0, 0.0), doodad_set=1)),
        SOUTH_ADT: fx.adt_bytes(SOUTH_M2, [SHRINE], SOUTH_DOODADS, [shrine_placement()]),
        NORTH_ADT: fx.adt_bytes(NORTH_M2, [SHRINE, FAR_HUT], NORTH_DOODADS, [shrine_placement(),
                                                                            far_hut_placement()]),
        SHRINE: shrine(), FAR_HUT: fx.wmo_root_bytes([("Set_$DefaultGlobal", 0, 0)], []),
        STONE: stock_stone(), skin_name(STONE): single_batch_skin(),
        LAMP_TREE: lamp_tree(), skin_name(LAMP_TREE): lamp_tree_skin(),
        BASIN: basin(), skin_name(BASIN): basin_skin(),
        LANTERN: simple_model("World\\Generic\\NightElf\\Passive Doodads\\Lanterns\\NE_Lantern.blp"),
        skin_name(LANTERN): single_batch_skin(),
        TENT: simple_model(ASHENVALE_DOODADS + "Tents\\Tent.blp"), skin_name(TENT): single_batch_skin(),
        BROKEN: b"MD21" + bytes(64),
    }
    return [FixtureFile(name, data, compression="zlib") for name, data in sorted(files.items())]


def build_data_folder(root):
    data = os.path.join(root, "Data")
    write_mpq(os.path.join(data, "common.MPQ"), stock_files(), version=2, listfile=True)
    write_mpq(os.path.join(data, "enUS", "locale-enUS.MPQ"),
              [FixtureFile(WORLD_MAP_AREA_DBC, fx.world_map_area_dbc_bytes([ASHENVALE, DARKSHORE, ELWYNN]),
                           compression="zlib")])
    write_mpq(os.path.join(data, "patch-A.MPQ"), [FixtureFile(STONE, hd_stone(), compression="zlib"),
                                                  FixtureFile(skin_name(STONE), hd_stone_skin(), compression="zlib"),
                                                  FixtureFile(LAMP_TREE, lamp_tree(), compression="zlib")])
    return data


def section(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


class ZoneCoordinates(unittest.TestCase):
    def test_x_runs_from_left_to_right_on_world_y_and_y_from_top_to_bottom_on_world_x(self):
        area = probe.WorldMapArea(*ASHENVALE)
        self.assertEqual(probe.zone_to_world(area, 0.0, 0.0), (area.top, area.left))
        corner = probe.zone_to_world(area, 100.0, 100.0)
        self.assertAlmostEqual(corner[0], area.bottom, places=3)
        self.assertAlmostEqual(corner[1], area.right, places=3)
        x, y = probe.zone_to_world(area, *MAESTRAS_POST)
        self.assertAlmostEqual(x, 3193.07, places=2)
        self.assertAlmostEqual(y, 177.60, places=2)

    def test_world_map_area_records_follow_the_3_3_5a_layout(self):
        table = parse_world_map_area_dbc(fx.world_map_area_dbc_bytes([ASHENVALE, ELWYNN]))
        self.assertEqual((table.fields, table.record_size), (11, 44))
        area = table.areas[0]
        self.assertEqual((area.record_id, area.map_id, area.area_id, area.name), (43, 1, 331, "Ashenvale"))
        self.assertEqual((area.left, area.right, area.top, area.bottom),
                         tuple(float32(value) for value in ASHENVALE[4:]))

    def test_tiles_near_a_point_cover_the_square_around_it(self):
        self.assertEqual(probe.tiles_near(POINT_A[0], POINT_A[1], 40.0), [(31, 25), (31, 26)])
        self.assertEqual(probe.tiles_near(POINT_B[0], POINT_B[1], 40.0), [(30, 26), (31, 26)])
        self.assertEqual(probe.tiles_near(0.0, 0.0, 1.0), [(31, 31), (32, 31), (31, 32), (32, 32)])


class Treatment(unittest.TestCase):
    def batches(self, model, skin):
        return parse_m2_materials("Fixture.m2", model, skin).batches

    def test_blend_mode_and_flags_pick_the_pass_and_the_fog_mode(self):
        hd = self.batches(hd_stone(), hd_stone_skin())
        self.assertEqual(probe.pass_text(hd[0]), "see-through pass (alpha 0.500 below 0.99999)")
        self.assertEqual(probe.fog_text(hd[0]), "stock fog mode 1 (the lighting's fog colour)")
        self.assertEqual(probe.pass_text(hd[1]), "see-through pass (blend 2 above 1)")
        tree = self.batches(lamp_tree(), lamp_tree_skin())
        self.assertEqual((probe.pass_text(tree[0]), probe.fog_text(tree[0])),
                         ("pass 0", "stock fog mode 1 (the lighting's fog colour)"))
        self.assertEqual(probe.fog_text(tree[1]), "stock fog mode 0 (unfogged: material flag 0x2)")
        modes = [probe.fog_text(batch) for batch in self.batches(basin(), basin_skin())]
        self.assertEqual(modes, ["stock fog mode 0 (unfogged)", "stock fog mode 3 (white)",
                                 "stock fog mode 4 (grey 0x80)", "stock fog mode 1 (the lighting's fog colour)"])

    def test_an_alpha_just_below_one_or_animated_across_it_is_named(self):
        nearly = self.batches(basin(), basin_skin())[3]
        self.assertEqual(probe.pass_text(nearly), "see-through pass (alpha 0.99997 below 0.99999)")
        self.assertEqual(probe.scalar_keys_text(nearly.transparency), "0.99997 static")
        animated = fx.m2_bytes(fx.M2Spec(materials=[(0, 0)], texture_lookup=[0], texture_unit_lookup=[0],
                                         textures=[fx.TextureSpec("Fade.blp")],
                                         texture_weights=[static_track(0, FIXED16_ONE)], transparency_lookup=[0]))
        batch = self.batches(animated, single_batch_skin())[0]
        self.assertEqual(probe.pass_text(batch), "pass 0 or the see-through pass as its alpha animates (0.000 to "
                                                 "1.000)")
        self.assertEqual(probe.scalar_keys_text(batch.transparency), "0.000 to 1.000 animated (2 keys)")

    def test_indices_outside_their_tables_are_noted(self):
        skin = fx.skin_bytes([fx.SubmeshSpec(index_count=3)],
                             [fx.BatchSpec(material=5, color=2, texture_combo=4, texture_weight_combo=9)])
        batch = self.batches(stock_stone(), skin)[0]
        self.assertEqual(batch.notes, ["material 5 is outside the table of 1", "colour 2 is outside the table of 0",
                                       "transparency lookup 9 is outside the table of 1",
                                       "texture 0 (lookup 4) is outside the tables"])
        self.assertEqual(probe.pass_text(batch), "pass unknown (no material)")
        self.assertEqual(probe.fog_text(batch), "stock fog mode unknown (no material)")

    def test_a_model_without_a_skin_or_with_an_old_header_says_so(self):
        self.assertEqual(parse_m2_materials("Fixture.m2", stock_stone(), None).notes, ["no skin"])
        old = fx.legacy_m2_bytes(256, (-1.0, -1.0, 0.0), (1.0, 1.0, 1.0), [])
        self.assertEqual(parse_m2_materials("Old.m2", old, None).notes,
                         ["version 256 predates the WotLK header; materials not read"])


class InspectModelsNear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        cls.data = build_data_folder(cls.root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def run_tool(self, *arguments):
        out = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = probe.main(list(arguments), out)
        return code, out.getvalue(), errors.getvalue()

    def inspect(self, *arguments):
        code, out, errors = self.run_tool("--data", self.data, *arguments)
        self.assertEqual(code, 0, out + errors)
        return out

    def test_the_models_near_maestras_post_come_nearest_first(self):
        out = self.inspect("--zone", "Ashenvale", "--at", "26.4,38.5")
        self.assertIn("\nzone Ashenvale: WorldMapArea 43, map 1, area 331, left 1700.00, right -4066.67, top 4672.92, "
                      "bottom 829.17\npoint 1: 26.4, 38.5 in Ashenvale -> world (3193.07, 177.60) on map 1 "
                      "Kalimdor\n", out)
        self.assertIn("\ntiles: Kalimdor_31_25.adt: 2 M2 placements, 2 WMO placements; Kalimdor_31_26.adt: 6 M2 "
                      "placements, 1 WMO placement\n", out)
        lines = out.splitlines()
        headers = [(line, lines[index + 1]) for index, line in enumerate(lines) if line.startswith("point 1 #")]
        self.assertEqual(headers, [
            ("point 1 #1 M2 " + STONE, "  5.0 yd away at (3196.07, 181.60, 100.00)"),
            ("point 1 #2 M2 " + LANTERN, "  10.4 yd away at (3183.07, 174.60, 101.00)"),
            ("point 1 #3 M2 " + LAMP_TREE, "  10.8 yd away at (3187.07, 186.60, 100.00)"),
            ("point 1 #4 M2 " + STONE, "  12.0 yd away at (3181.07, 177.60, 100.00)"),
            ("point 1 #5 M2 " + BASIN, "  20.6 yd away at (3213.07, 172.60, 100.00)"),
            ("point 1 #6 M2 " + GHOST, "  30.0 yd away at (3193.07, 147.60, 100.00)"),
            ("point 1 #7 M2 " + BROKEN, "  35.0 yd away at (3193.07, 212.60, 100.00)")])
        self.assertIn("\n  placed by Kalimdor_31_25.adt (MDDF), unique id 7001, rotation (0.0, 135.0, 0.0), scale "
                      "1.00, flags 0x0\n  file: patch-A.MPQ (custom); lower versions: common.MPQ (stock)\n  skin 00: "
                      "patch-A.MPQ (custom)\n", out)
        self.assertIn("\n  placed by WMO %s (unique id 900), doodad set 1 Set_Night, doodad 1, scale 1.00\n" % SHRINE,
                      out)
        self.assertIn("\n  placed by WMO %s (unique id 900), doodad set 0 Set_$DefaultGlobal, doodad 0, scale 1.00\n"
                      "  same model as point 1 #1\n" % SHRINE, out)
        self.assertIn("\n  placed by Kalimdor_31_26.adt (MDDF), unique id 7004, rotation (0.0, 0.0, 0.0), scale 1.00, "
                      "flags 0x0\n  missing file\n", out)
        self.assertIn("\n  file: common.MPQ (stock)\n  parse error: %s: magic b'MD21' is not MD20\n"
                      % lw.model_key(BROKEN), out)
        for absent in (TENT, TORCH, FAR_HUT):
            self.assertNotIn(absent, out)

    def test_every_batch_shows_its_material_values_and_the_clients_treatment(self):
        out = self.inspect("--zone", "Ashenvale", "--at", "26.4,38.5")
        stone = section(out, "point 1 #1 M2", "point 1 #2 M2")
        self.assertIn(
            "  M2 version 264, global flags 0x0, 1 skin profile, box (-1.50, -1.00, 0.00) to (1.50, 1.00, 3.00), "
            "2 sequences (1 in .anim files), 2 textures\n"
            "  render batches in skin 00: 2\n"
            "    batch 0: submesh 0 (900 indices), priority plane 0, material layer 0, batch flags 0x10\n"
            "      material 0: blend 1 (alpha key), flags 0x4 (two-sided)\n"
            "      shader 0x11, 2 textures: " + ASHENVALE_DOODADS + "Runestones\\Runestone_HD.blp (uv 0); "
            "(replaceable type 2) (environment map)\n"
            "      colour 0: rgb (0.25, 0.25, 0.30) static, alpha 0.500 static\n"
            "      transparency lookup 0 -> weight 0: 1.000 static\n"
            "      client: see-through pass (alpha 0.500 below 0.99999), stock fog mode 1 (the lighting's fog "
            "colour)\n"
            "    batch 1: submesh 1 (120 indices), priority plane 1, material layer 1, batch flags 0x0\n"
            "      material 1: blend 2 (alpha), flags 0x0\n"
            "      shader 0x0, 1 texture: " + ASHENVALE_DOODADS + "Runestones\\Runestone_HD.blp (uv 0)\n"
            "      colour none\n"
            "      transparency lookup 1 -> weight 1: 0.250 to 1.000 animated (2 keys), 1 sequence in .anim files "
            "not read\n"
            "      client: see-through pass (blend 2 above 1), stock fog mode 1 (the lighting's fog colour)\n", stone)
        tree = section(out, "point 1 #3 M2", "point 1 #4 M2")
        self.assertIn("  skin 00: common.MPQ (stock), another archive than the model\n", tree)
        self.assertIn(
            "      material 1: blend 4 (add), flags 0x3 (unlit, unfogged)\n"
            "      shader 0x0, 1 texture: " + ASHENVALE_DOODADS + "Trees\\LampTreeGlow.blp (uv 0)\n"
            "      colour 0: rgb (0.20, 0.40, 1.00) to (0.40, 0.60, 1.00) animated (2 keys), alpha 1.000 static\n"
            "      transparency lookup 0 -> weight 0: 1.000 static\n"
            "      client: see-through pass (blend 4 above 1), stock fog mode 0 (unfogged: material flag 0x2)\n", tree)
        basin_text = section(out, "point 1 #5 M2", "point 1 #6 M2")
        self.assertIn("global flags 0x8, ", basin_text)
        self.assertIn("      material 0: blend 7 (blend add), flags 0x0\n"
                      "      shader 0x1, combiner combos [5], 1 texture", basin_text)
        self.assertIn("      client: see-through pass (blend 7 above 1), stock fog mode 0 (unfogged)\n", basin_text)
        self.assertIn("      client: see-through pass (blend 5 above 1), stock fog mode 3 (white)\n", basin_text)
        self.assertIn("      client: see-through pass (blend 6 above 1), stock fog mode 4 (grey 0x80)\n", basin_text)
        self.assertIn("      transparency lookup 1 -> weight 1: 0.99997 static\n      client: see-through pass (alpha "
                      "0.99997 below 0.99999), stock fog mode 1 (the lighting's fog colour)\n", basin_text)

    def test_wmos_near_the_point_list_their_materials_fogs_and_doodad_sets(self):
        out = self.inspect("--zone", "Ashenvale", "--at", "26.4,38.5")
        self.assertIn(
            "WMOs within 40.0 yd of point 1, nearest first: 1\n"
            "point 1 WMO #1 WMO " + SHRINE + "\n"
            "  2.0 yd away, at (3183.07, 177.60, 100.00), box (3175.07, 169.60, 90.00) to (3191.07, 185.60, 110.00)\n"
            "  placed by Kalimdor_31_25.adt (MODF), unique id 900, rotation (0.0, 0.0, 0.0), doodad set 1, flags 0x0\n"
            "  file: common.MPQ (stock)\n"
            "  WMO header flags 0x1, 3 groups, ambient 0xFF000000, 2 materials, 1 fog\n"
            "  material 0: blend 0 (opaque), flags 0x8 (exterior light), shader 0, sidn 0x00000000, diffuse "
            "0xFF404040, textures Shrine_Wall.blp\n"
            "  material 1: blend 1 (alpha key), flags 0x3 (unlit, unfogged), shader 6, sidn 0xFF6080FF, diffuse "
            "0x00000000, textures Shrine_Glow.blp, Shrine_Glow2.blp\n"
            "  fog 0: flags 0x0, at (0.00, 0.00, 0.00), radius 0.0 to 0.0, end 444.5, start x0.25, colour 0xFF203040, "
            "under water end 222.2, start x-0.50, colour 0xFF000000\n"
            "  doodad sets: 0 Set_$DefaultGlobal (1 doodad); 1 Set_Night (1 doodad); 2 Set_Day (1 doodad)\n", out)

    def test_a_world_position_gives_the_same_survey_as_its_zone_coordinate(self):
        by_zone = self.inspect("--zone", "ashenVALE", "--at", "26.4,38.5")
        by_world = self.inspect("--map", "1", "--world", "%.4f,%.4f" % POINT_A)
        self.assertIn("point 1: world %.2f, %.2f -> world (3193.07, 177.60) on map 1 Kalimdor\n" % POINT_A, by_world)
        start = "M2 models within"
        self.assertEqual(by_world[by_world.index(start):], by_zone[by_zone.index(start):])

    def test_split_or_spaced_pairs_read_like_one(self):
        joined = self.inspect("--zone", "Ashenvale", "--at", "26.4,38.5")
        for pair in (["26.4", "38.5"], ["26.4,", "38.5"], ["26.4, 38.5"]):
            with self.subTest(pair=pair):
                self.assertEqual(self.inspect("--zone", "Ashenvale", "--at", *pair), joined)

    def test_several_points_name_the_models_near_every_point(self):
        out = self.inspect("--zone", "Ashenvale", "--at", "26.4,38.5", "20.4,42.7", "--radius", "20")
        self.assertIn("point 2: 20.4, 42.7 in Ashenvale -> world (3031.64, 523.60) on map 1 Kalimdor\n", out)
        self.assertIn("\ntiles: Kalimdor_30_26.adt: not in the WDT; Kalimdor_31_26.adt: 6 M2 placements, 1 WMO "
                      "placement\n", out)
        self.assertIn("\npoint 2 #1 M2 %s\n  1.4 yd away at (3032.64, 522.60, 100.00)\n  placed by "
                      "Kalimdor_31_26.adt (MDDF), unique id 7002, rotation (0.0, 0.0, 0.0), scale 1.00, flags 0x0\n"
                      "  same model as point 1 #1\n" % STONE, out)
        self.assertIn("M2 models within 20.0 yd of point 2, nearest first: 1\n", out)
        self.assertTrue(out.endswith("\nM2 models near every point: 1\n  %s: point 1 #1 at 5.0 yd; point 2 #1 at "
                                     "1.4 yd\n" % STONE), out[-400:])

    def test_a_global_wmo_is_listed_with_its_doodads(self):
        out = self.inspect("--map", str(INSTANCE_MAP), "--world", "0,0")
        self.assertIn("tiles: Shadowfang_31_31.adt: not in the WDT; Shadowfang_32_31.adt: not in the WDT; "
                      "Shadowfang_31_32.adt: not in the WDT; Shadowfang_32_32.adt: not in the WDT\n", out)
        self.assertIn("\npoint 1 #1 M2 %s\n  2.0 yd away at (-2.00, 0.00, 0.00)\n" % STONE, out)
        self.assertIn("\npoint 1 #2 M2 %s\n  3.0 yd away at (0.00, -3.00, 1.00)\n" % LANTERN, out)
        self.assertIn("\npoint 1 WMO #1 WMO %s\n  0.0 yd away, at (0.00, 0.00, 0.00)" % SHRINE, out)
        self.assertIn("  placed by WDT (global WMO), unique id 77, rotation (0.0, 0.0, 0.0), doodad set 1, flags "
                      "0x0\n", out)

    def test_model_mode_describes_files_without_a_point(self):
        out = self.inspect("--model", STONE.lower().replace("\\", "/")[:-3] + ".mdx", SHRINE)
        stone = STONE.lower()
        self.assertIn("\nM2 %s\n  file: patch-A.MPQ (custom); lower versions: common.MPQ (stock)\n  skin 00: "
                      "patch-A.MPQ (custom)\n  M2 version 264, " % stone, out)
        self.assertIn("\nWMO %s\n  file: common.MPQ (stock)\n  WMO header flags 0x1, 3 groups" % SHRINE, out)
        self.assertNotIn("point 1", out)

    def test_an_unknown_zone_or_map_exits_with_1(self):
        code, out, _ = self.run_tool("--data", self.data, "--zone", "Atlantis", "--at", "1,2")
        self.assertEqual(code, 1)
        self.assertIn("no zone Atlantis in WorldMapArea.dbc; its names: Ashenvale, Darkshore, Elwynn\n", out)
        code, out, _ = self.run_tool("--data", self.data, "--map", "99", "--world", "1,2")
        self.assertEqual(code, 1)
        self.assertIn("map 99 is not in DBFilesClient\\Map.dbc\n", out)

    def test_missing_archives_or_tables_exit_with_1(self):
        empty = os.path.join(self.root, "empty", "Data")
        os.makedirs(empty)
        code, out, _ = self.run_tool("--data", empty, "--map", "1", "--world", "1,2")
        self.assertEqual(code, 1)
        self.assertIn("no MPQ archive found in", out)
        bare = os.path.join(self.root, "bare", "Data")
        write_mpq(os.path.join(bare, "common.MPQ"), [FixtureFile(MAP_DBC, fx.map_dbc_bytes([(1, "Kalimdor")]))])
        code, out, _ = self.run_tool("--data", bare, "--zone", "Ashenvale", "--at", "26.4,38.5")
        self.assertEqual(code, 1)
        self.assertIn("no DBFilesClient\\WorldMapArea.dbc in any archive\n", out)
        code, out, _ = self.run_tool("--data", bare, "--map", "1", "--world", "1,2")
        self.assertEqual(code, 0, out)
        self.assertIn("note: no World\\Maps\\Kalimdor\\Kalimdor.wdt in any archive\n", out)
        self.assertIn("nothing placed there: server-spawned objects and creatures are not in the map files\n", out)

    def test_usage_errors_exit_with_2(self):
        for arguments in ([], ["--data", self.data], ["--data", self.data, "--zone", "Ashenvale"],
                          ["--data", self.data, "--at", "26.4,38.5"],
                          ["--data", self.data, "--map", "1"], ["--data", self.data, "--world", "1,2"],
                          ["--data", self.data, "--zone", "Ashenvale", "--at", "1,2", "--map", "1"],
                          ["--data", self.data, "--zone", "Ashenvale", "--at", "26,4,38"],
                          ["--data", self.data, "--zone", "Ashenvale", "--at", "north,east"],
                          ["--data", self.data, "--zone", "Ashenvale", "--at", "1,2", "--radius", "0"],
                          ["--data", self.data, "--zone", "Ashenvale", "--at", "1,2", "--radius", "-5"],
                          ["--data", self.data, "--model", STONE, "--map", "1", "--world", "1,2"],
                          ["--data", os.path.join(self.root, "no-such-folder"), "--map", "1", "--world", "1,2"]):
            with self.subTest(arguments=arguments):
                code, _, errors = self.run_tool(*arguments)
                self.assertEqual(code, 2)
                self.assertIn("error", errors)

    def test_the_script_runs_from_the_command_line(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        environment.pop("PYTHONPATH", None)
        finished = subprocess.run([sys.executable, os.path.join(TOOLS, "inspect_models_near.py"), "--data", self.data,
                                   "--zone", "Ashenvale", "--at", "26.4,38.5"],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                                  universal_newlines=True, timeout=120)
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertIn("M2 models within 40.0 yd of point 1, nearest first: 7\n", finished.stdout)


if __name__ == "__main__":
    unittest.main()
