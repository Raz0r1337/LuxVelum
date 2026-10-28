import math
import struct
import unittest

import format_fixtures as fx
import lamp_formats as lf
import lamp_rules as lr
from lamp_formats import FormatError

QUARTER_TURN_Z = (0.0, 0.0, math.sqrt(0.5), math.sqrt(0.5))


def light_model(*lights, bones=(), sequences=None, skin=None, **spec):
    model_spec = fx.M2Spec(lights=list(lights), bones=list(bones), **spec)
    if sequences is not None:
        model_spec.sequences = sequences
    return lf.parse_m2("World\\Fixture\\Lamp.m2", fx.m2_bytes(model_spec), skin)


class RecordSizes(unittest.TestCase):
    def test_wotlk_record_sizes_match_pywowlib(self):
        self.assertEqual(lf.M2_LIGHT_SIZE, 156)
        self.assertEqual(lf.M2_PARTICLE_SIZE, 476)
        self.assertEqual(lf.M2_SEQUENCE_SIZE, 64)
        self.assertEqual(lf.M2_BONE_SIZE, 88)
        self.assertEqual(lf.SKIN_SUBMESH_SIZE, 48)
        self.assertEqual(lf.SKIN_BATCH_SIZE, 24)
        self.assertEqual(lf.M2_TRACK_SIZE, 20)
        self.assertEqual(lf.M2_TEXTURE.size, 16)
        self.assertEqual(lf.MDDF_RECORD.size, 36)
        self.assertEqual(lf.MODF_RECORD.size, 64)
        self.assertEqual(lf.MODS_RECORD.size, 32)
        self.assertEqual(lf.MODD_RECORD.size, 40)
        self.assertEqual(lf.SKIN_BATCH.size, 18)

    def test_field_offsets_end_inside_their_records(self):
        self.assertEqual(lf.BONE_PIVOT + lf.VEC3.size, lf.M2_BONE_SIZE)
        self.assertEqual(lf.LIGHT_VISIBILITY + lf.M2_TRACK_SIZE, lf.M2_LIGHT_SIZE)
        self.assertEqual(lf.SUBMESH_CENTER, 0x14)
        self.assertEqual(lf.EMITTER_EMISSION_RATE, 176)
        self.assertEqual(lf.EMITTER_SCALE + 16 + 8 + 2 * 16, 348)

    def test_wotlk_header_offsets_follow_the_spec(self):
        layout = lf.WOTLK_LAYOUT
        self.assertEqual((layout.sequences, layout.bones, layout.textures, layout.materials, layout.texture_lookup),
                         (0x1C, 0x2C, 0x50, 0x70, 0x80))
        self.assertEqual((layout.bounds_min, layout.bounds_max, layout.lights, layout.emitters),
                         (0xA0, 0xAC, 0x108, 0x128))

    def test_fixture_records_have_pywowlib_sizes(self):
        arena = fx.Arena(0)
        self.assertEqual(len(fx.sequence_record(fx.SequenceSpec())), 64)
        self.assertEqual(len(fx.bone_record(arena, fx.BoneSpec(translation=(1.0, 2.0, 3.0)))), 88)
        self.assertEqual(len(fx.light_record(arena, fx.LightSpec())), 156)
        self.assertEqual(len(fx.particle_record(arena, fx.EmitterSpec())), 476)
        self.assertEqual(len(fx.submesh_record(fx.SubmeshSpec())), 48)
        self.assertEqual(len(fx.batch_record(fx.BatchSpec())), 24)
        self.assertEqual(len(fx.m2_bytes(fx.M2Spec())[:fx.M2_HEADER_SIZE]), 0x130)


class MapDbc(unittest.TestCase):
    def test_reads_ids_and_directories(self):
        data = fx.map_dbc_bytes([(0, "Azeroth"), (530, "Expansion01")])
        self.assertEqual(lf.parse_map_dbc(data), [(0, "Azeroth"), (530, "Expansion01")])

    def test_rejects_wrong_magic(self):
        data = b"WDBX" + fx.map_dbc_bytes([(0, "Azeroth")])[4:]
        with self.assertRaises(FormatError):
            lf.parse_map_dbc(data)

    def test_rejects_truncated_string_block(self):
        data = fx.map_dbc_bytes([(0, "Azeroth")])
        with self.assertRaises(FormatError):
            lf.parse_map_dbc(data[:-3])

    def test_rejects_directory_offset_outside_strings(self):
        data = bytearray(fx.map_dbc_bytes([(1, "Kalimdor")]))
        struct.pack_into("<I", data, 20 + 4, 999)
        with self.assertRaises(FormatError):
            lf.parse_map_dbc(bytes(data))


class Wdt(unittest.TestCase):
    def test_tiles_are_column_then_row(self):
        wdt = lf.parse_wdt(fx.wdt_bytes([(5, 3), (0, 0), (63, 63)]))
        self.assertEqual(wdt.tiles, [(0, 0), (5, 3), (63, 63)])
        self.assertIsNone(wdt.global_wmo)
        self.assertIsNone(wdt.global_wmo_placement)

    def test_main_entry_for_row_three_column_five_is_tile_five_three(self):
        data = bytearray(fx.wdt_bytes([]))
        main_data = data.index(b"NIAM") + 8
        struct.pack_into("<I", data, main_data + (3 * 64 + 5) * 8, 1)
        self.assertEqual(lf.parse_wdt(bytes(data)).tiles, [(5, 3)])

    def test_global_wmo_needs_the_mphd_flag(self):
        placement = fx.WmoPlacement(0, 77, (0.0, 12.0, 0.0), doodad_set=1)
        wdt = lf.parse_wdt(fx.wdt_bytes([], "World\\wmo\\Dungeon\\Crypt.wmo", placement))
        self.assertEqual(wdt.tiles, [])
        self.assertEqual(wdt.global_wmo, "World\\wmo\\Dungeon\\Crypt.wmo")
        self.assertEqual(wdt.global_wmo_placement.unique_id, 77)
        self.assertEqual(wdt.global_wmo_placement.doodad_set, 1)
        self.assertEqual(wdt.global_wmo_placement.position, (0.0, 12.0, 0.0))
        unflagged = lf.parse_wdt(fx.wdt_bytes([], "World\\wmo\\Dungeon\\Crypt.wmo", placement, flags=0))
        self.assertIsNone(unflagged.global_wmo)

    def test_rejects_short_main(self):
        data = fx.chunk(b"MVER", struct.pack("<I", 18)) + fx.chunk(b"MAIN", b"\0" * 100)
        with self.assertRaises(FormatError):
            lf.parse_wdt(data)

    def test_rejects_chunk_running_past_the_end(self):
        with self.assertRaises(FormatError):
            lf.parse_wdt(fx.wdt_bytes([(1, 1)])[:-10])


def sample_adt():
    doodads = [fx.DoodadPlacement(0, 11, (100.0, 50.0, 200.0), (0.0, 90.0, 0.0), 2048, 1),
               fx.DoodadPlacement(1, 12, (1.0, 2.0, 3.0)),
               fx.DoodadPlacement(7, 13, (4.0, 5.0, 6.0))]
    wmos = [fx.WmoPlacement(0, 21, (10.0, 20.0, 30.0), (1.0, 2.0, 3.0), (-1.0, -2.0, -3.0), (4.0, 5.0, 6.0),
                            flags=2, doodad_set=3, name_set=4)]
    return fx.adt_bytes(["World\\Torch.mdx", "World\\Lamp.M2"], ["World\\wmo\\Inn.wmo"], doodads, wmos)


class Adt(unittest.TestCase):
    def test_prefix_size_grows_to_the_end_of_modf(self):
        data = sample_adt()
        modf_end = data.index(b"KNCM")
        modf_start = data.index(b"FDOM")
        self.assertEqual(lf.adt_prefix_size(data[:lf.ADT_HEADER_SIZE]), modf_start + 8)
        self.assertEqual(lf.adt_prefix_size(data[:modf_start + 8]), modf_end)
        self.assertEqual(lf.adt_prefix_size(data), modf_end)
        self.assertLess(modf_end, len(data))

    def test_placements_and_names_from_prefix(self):
        data = sample_adt()
        adt = lf.parse_adt(data[:lf.adt_prefix_size(data)])
        self.assertEqual(adt.m2_names, ["World\\Torch.m2", "World\\Lamp.M2"])
        self.assertEqual(adt.wmo_names, ["World\\wmo\\Inn.wmo"])
        first = adt.doodads[0]
        self.assertEqual((first.name, first.unique_id, first.position, first.rotation, first.scale, first.flags),
                         ("World\\Torch.m2", 11, (100.0, 50.0, 200.0), (0.0, 90.0, 0.0), 2048, 1))
        self.assertEqual(adt.doodads[1].name, "World\\Lamp.M2")
        self.assertEqual(adt.doodads[2].name, "")
        wmo = adt.wmos[0]
        self.assertEqual((wmo.name, wmo.unique_id, wmo.position, wmo.rotation), ("World\\wmo\\Inn.wmo", 21,
                                                                                  (10.0, 20.0, 30.0),
                                                                                  (1.0, 2.0, 3.0)))
        self.assertEqual((wmo.extents_min, wmo.extents_max), ((-1.0, -2.0, -3.0), (4.0, 5.0, 6.0)))
        self.assertEqual((wmo.flags, wmo.doodad_set, wmo.name_set), (2, 3, 4))
        self.assertEqual(lf.parse_adt(data), adt)

    def test_rejects_mhdr_pointing_at_another_chunk(self):
        data = bytearray(sample_adt())
        struct.pack_into("<I", data, lf.MHDR_DATA_START + 4 * 8, data.index(b"XETM") - lf.MHDR_DATA_START)
        with self.assertRaises(FormatError):
            lf.adt_prefix_size(bytes(data))

    def test_rejects_too_short_and_wrong_header(self):
        data = sample_adt()
        with self.assertRaises(FormatError):
            lf.adt_prefix_size(data[:40])
        with self.assertRaises(FormatError):
            lf.parse_adt(b"XXXX" + data[4:])

    def test_rejects_prefix_cut_inside_a_placement_chunk(self):
        data = sample_adt()
        with self.assertRaises(FormatError):
            lf.parse_adt(data[:data.index(b"KNCM") - 4])


class WmoRoot(unittest.TestCase):
    def test_sets_and_doodads(self):
        doodads = [fx.WmoDoodadSpec("World\\Candle.MDX", (1.0, 2.0, 3.0), (0.0, 0.0, 0.5, 0.5), 1.5, flags=0x3),
                   fx.WmoDoodadSpec("World\\Chair.m2")]
        root = lf.parse_wmo_root(fx.wmo_root_bytes([("Set_$DefaultGlobal", 0, 1), ("Set_Party", 1, 1)], doodads))
        self.assertEqual(root.doodad_sets, [("Set_$DefaultGlobal", 0, 1), ("Set_Party", 1, 1)])
        self.assertEqual(root.doodads[0], ("World\\Candle.m2", (1.0, 2.0, 3.0), (0.0, 0.0, 0.5, 0.5), 1.5))
        self.assertEqual(root.doodads[1].name, "World\\Chair.m2")
        self.assertEqual(root.doodads[1].rotation, (0.0, 0.0, 0.0, 1.0))

    def test_rejects_group_file(self):
        data = fx.chunk(b"MVER", struct.pack("<I", 17)) + fx.chunk(b"MOGP", b"\0" * 68)
        with self.assertRaises(FormatError):
            lf.parse_wmo_root(data)


class M2Header(unittest.TestCase):
    def test_bounds_version_and_textures(self):
        model = light_model(textures=[fx.TextureSpec("World\\Fire.blp"), fx.TextureSpec("", texture_type=11)],
                            bounds_min=(-2.0, -3.0, 0.5), bounds_max=(2.0, 3.0, 4.5))
        self.assertEqual(model.version, 264)
        self.assertEqual(model.path, "World\\Fixture\\Lamp.m2")
        self.assertEqual((model.bounds_min, model.bounds_max), ((-2.0, -3.0, 0.5), (2.0, 3.0, 4.5)))
        self.assertEqual(model.textures, ["World\\Fire.blp", ""])
        self.assertEqual(model.notes, ["no skin"])

    def test_rejects_wrong_magic_and_truncation(self):
        data = fx.m2_bytes(fx.M2Spec(lights=[fx.LightSpec()]))
        with self.assertRaises(FormatError):
            lf.parse_m2("A.m2", b"MD21" + data[4:])
        with self.assertRaises(FormatError):
            lf.parse_m2("A.m2", data[:0x100])
        broken = bytearray(data)
        struct.pack_into("<2I", broken, 0x108, 3, len(data) - 200)
        with self.assertRaises(FormatError):
            lf.parse_m2("A.m2", bytes(broken))

    def test_legacy_version_reads_bounds_and_textures(self):
        data = fx.legacy_m2_bytes(260, (0.0, 0.0, 0.0), (1.0, 2.0, 3.0), [fx.TextureSpec("Old.blp")])
        model = lf.parse_m2("Old.m2", data)
        self.assertEqual((model.version, model.bounds_max, model.textures), (260, (1.0, 2.0, 3.0), ["Old.blp"]))
        self.assertEqual((model.lights, model.emitters, model.batches), ([], [], []))
        self.assertIn("pre-WotLK", model.notes[0])
        self.assertEqual(lf.m2_light_count(data), 1)

    def test_later_version_uses_the_wotlk_layout_with_a_note(self):
        model = light_model(fx.LightSpec(), version=265)
        self.assertEqual(len(model.lights), 1)
        self.assertIn("version 265", model.notes[0])

    def test_light_count_from_header(self):
        self.assertEqual(lf.m2_light_count(fx.m2_bytes(fx.M2Spec(lights=[fx.LightSpec(), fx.LightSpec()]))), 2)
        with self.assertRaises(FormatError):
            lf.m2_light_count(b"SKIN" + b"\0" * 400)


class M2Lights(unittest.TestCase):
    def test_first_keys_of_the_light_tracks(self):
        spec = fx.LightSpec(light_type=1, position=(1.0, 2.0, 3.0), diffuse_color=(0.9, 0.6, 0.3),
                            diffuse_intensity=1.5, attenuation_start=2.0, attenuation_end=7.5)
        light = light_model(spec).lights[0]
        self.assertEqual((light.light_type, light.bone, light.position), (1, -1, (1.0, 2.0, 3.0)))
        for actual, expected in zip(light.diffuse_color, (0.9, 0.6, 0.3)):
            self.assertAlmostEqual(actual, expected, places=6)
        self.assertEqual((light.diffuse_intensity, light.attenuation_start, light.attenuation_end), (1.5, 2.0, 7.5))
        self.assertTrue(light.visible)

    def test_visibility(self):
        model = light_model(fx.LightSpec(visibility=0), fx.LightSpec(visibility=1), fx.LightSpec(visibility=None),
                            fx.LightSpec(light_type=0))
        self.assertEqual([light.visible for light in model.lights], [False, True, True, True])
        self.assertEqual(model.lights[3].light_type, 0)

    def test_tracks_without_keys_use_defaults(self):
        light = light_model(fx.LightSpec(diffuse_color=None, diffuse_intensity=None, attenuation_start=None,
                                         attenuation_end=None)).lights[0]
        self.assertEqual((light.diffuse_color, light.diffuse_intensity, light.attenuation_end),
                         ((0.0, 0.0, 0.0), 0.0, 0.0))

    def test_sequence_stored_outside_the_model_is_not_read(self):
        light = light_model(fx.LightSpec(diffuse_intensity=2.0), sequences=[fx.SequenceSpec(flags=0)]).lights[0]
        self.assertEqual(light.diffuse_intensity, 0.0)
        self.assertTrue(light.visible)
        no_sequences = light_model(fx.LightSpec(diffuse_intensity=2.0), sequences=[]).lights[0]
        self.assertEqual(no_sequences.diffuse_intensity, 0.0)

    def test_global_sequence_tracks_are_always_in_the_model(self):
        spec = fx.LightSpec(diffuse_intensity=2.0, global_sequence=0)
        light = light_model(spec, sequences=[fx.SequenceSpec(flags=0)]).lights[0]
        self.assertEqual(light.diffuse_intensity, 2.0)


class M2RestPose(unittest.TestCase):
    def assertPoint(self, actual, expected):
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, places=3)

    def test_light_on_a_bone_moves_by_the_first_translation_key(self):
        model = light_model(fx.LightSpec(bone=0, position=(1.0, 0.0, 0.0)),
                            bones=[fx.BoneSpec(translation=(0.0, 0.0, 2.0))])
        self.assertPoint(model.lights[0].position, (1.0, 0.0, 2.0))

    def test_parent_chain_with_pivot_and_rotation(self):
        bones = [fx.BoneSpec(pivot=(1.0, 0.0, 0.0), translation=(0.0, 0.0, 1.0), rotation=QUARTER_TURN_Z),
                 fx.BoneSpec(parent=0, translation=(2.0, 0.0, 0.0))]
        model = light_model(fx.LightSpec(bone=1, position=(0.0, 1.0, 0.0)), bones=bones)
        self.assertPoint(model.lights[0].position, (0.0, 1.0, 1.0))

    def test_scale_about_the_pivot(self):
        model = light_model(fx.LightSpec(bone=0, position=(1.0, 0.0, 1.0)),
                            bones=[fx.BoneSpec(pivot=(0.0, 0.0, 1.0), scale=(2.0, 2.0, 2.0))])
        self.assertPoint(model.lights[0].position, (2.0, 0.0, 1.0))

    def test_scale_then_rotation_then_translation(self):
        bone = fx.BoneSpec(translation=(1.0, 0.0, 0.0), rotation=QUARTER_TURN_Z, scale=(2.0, 1.0, 1.0))
        model = light_model(fx.LightSpec(bone=0, position=(1.0, 0.0, 0.0)), bones=[bone])
        self.assertPoint(model.lights[0].position, (1.0, 2.0, 0.0))

    def test_identity_when_keys_are_unavailable(self):
        position = (1.0, 2.0, 3.0)
        detached = light_model(fx.LightSpec(bone=0, position=position),
                               bones=[fx.BoneSpec(translation=(5.0, 5.0, 5.0), detached=True)])
        self.assertPoint(detached.lights[0].position, position)
        outside = light_model(fx.LightSpec(bone=0, position=position),
                              bones=[fx.BoneSpec(translation=(5.0, 5.0, 5.0))], sequences=[fx.SequenceSpec(0)])
        self.assertPoint(outside.lights[0].position, position)
        out_of_range = light_model(fx.LightSpec(bone=4, position=position),
                                   bones=[fx.BoneSpec(translation=(5.0, 5.0, 5.0))])
        self.assertPoint(out_of_range.lights[0].position, position)

    def test_parent_cycle_ends(self):
        bones = [fx.BoneSpec(parent=1, translation=(1.0, 0.0, 0.0)), fx.BoneSpec(parent=0, translation=(0.0, 1.0, 0.0))]
        model = light_model(fx.LightSpec(bone=0), bones=bones)
        self.assertPoint(model.lights[0].position, (1.0, 1.0, 0.0))

    def test_compressed_quaternion_components(self):
        self.assertEqual([lf.decompressed_component(value) for value in (32767, -1, 0, -32768)],
                         [0.0, 1.0, -1.0, 0.0])
        self.assertAlmostEqual(lf.decompressed_component(-16384), 16384 / 32767)


class M2Emitters(unittest.TestCase):
    def test_emitter_fields(self):
        spec = fx.EmitterSpec(bone=0, position=(0.0, 0.0, 1.0), texture=1, blend=4, emission_rate=12.5,
                              colors=[(255.0, 102.0, 51.0)], alphas=[32767, 16383], sizes=[(0.75, 0.1)])
        model = light_model(emitters=[spec], bones=[fx.BoneSpec(translation=(0.0, 0.0, 2.0))],
                            textures=[fx.TextureSpec("", texture_type=2), fx.TextureSpec("World\\Flame.blp")])
        emitter = model.emitters[0]
        self.assertEqual((emitter.bone, emitter.position, emitter.texture, emitter.blend, emitter.emission_rate),
                         (0, (0.0, 0.0, 3.0), "World\\Flame.blp", 4, 12.5))
        self.assertEqual(emitter.colors, [(1.0, 0.4, 0.2)])
        self.assertEqual(emitter.alphas, [1.0, 16383 / 32767])
        self.assertAlmostEqual(emitter.sizes[0], 0.75)

    def test_replaceable_texture_and_missing_rate(self):
        spec = fx.EmitterSpec(texture=0, emission_rate=None)
        emitter = light_model(emitters=[spec], textures=[fx.TextureSpec("", texture_type=1)]).emitters[0]
        self.assertEqual((emitter.texture, emitter.emission_rate), ("", 0.0))

    def test_emission_rate_is_the_peak_of_the_first_sequence(self):
        for keys, rate in (([0.0, 20.0, 5.0], 20.0), ([math.nan, 3.0], 3.0), ([math.nan], 0.0), ([], 0.0)):
            with self.subTest(keys=keys):
                spec = fx.EmitterSpec(texture=0, emission_rate_keys=keys)
                emitter = light_model(emitters=[spec], textures=[fx.TextureSpec("A.blp")]).emitters[0]
                self.assertEqual(emitter.emission_rate, rate)

    def test_a_flame_that_ramps_in_from_zero_still_burns(self):
        spec = fx.EmitterSpec(texture=0, emission_rate_keys=[0.0, 16.0], sizes=[(0.3, 0.3)])
        model = light_model(emitters=[spec], textures=[fx.TextureSpec("World\\Generic\\Fire\\TorchFlame.blp")])
        self.assertTrue(lr.fire_emitter(model.emitters[0]))
        self.assertAlmostEqual(lr.fire_strength(model.emitters[0]), 0.6, places=6)

    def test_texture_outside_the_table_is_noted(self):
        model = light_model(emitters=[fx.EmitterSpec(texture=5)], textures=[fx.TextureSpec("A.blp")])
        self.assertEqual(model.emitters[0].texture, "")
        self.assertIn("emitter texture 5 is outside the table of 1", model.notes)


class M2Batches(unittest.TestCase):
    def model_with(self, skin):
        return light_model(textures=[fx.TextureSpec("World\\Glass.blp"), fx.TextureSpec("World\\Glow.blp")],
                           materials=[(0x0, 0), (0x1, 2)], texture_lookup=[1, 0], skin=skin)

    def test_batches_from_skin(self):
        skin = fx.skin_bytes([fx.SubmeshSpec((1.0, 2.0, 3.0), 36), fx.SubmeshSpec((0.0, 0.0, 4.0), 12)],
                             [fx.BatchSpec(submesh=1, material=1, texture_combo=0),
                              fx.BatchSpec(submesh=0, material=0, texture_combo=1)])
        batches = self.model_with(skin).batches
        self.assertEqual([(batch.unlit, batch.blend, batch.texture, batch.center, batch.index_count)
                          for batch in batches],
                         [(True, 2, "World\\Glow.blp", (0.0, 0.0, 4.0), 12),
                          (False, 0, "World\\Glass.blp", (1.0, 2.0, 3.0), 36)])

    def test_unreadable_skin_keeps_the_model(self):
        model = self.model_with(b"NIKS" + b"\0" * 44)
        self.assertEqual(model.batches, [])
        self.assertTrue(model.notes[0].startswith("batches unreadable"))
        bad_index = fx.skin_bytes([fx.SubmeshSpec()], [fx.BatchSpec(material=9)])
        self.assertEqual(self.model_with(bad_index).batches, [])

    def test_skin_path(self):
        self.assertEqual(lf.skin_path("WORLD\\LAMP.M2"), "WORLD\\LAMP00.skin")
        self.assertIsNone(lf.skin_path("WORLD\\LAMP.WMO"))


if __name__ == "__main__":
    unittest.main()
