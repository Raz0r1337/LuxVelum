import math
import unittest

import lamp_rules as lr
from lamp_types import (FLAG_BOUNDS_FALLBACK, FLAG_CLAMPED_TO_MODEL, FLAG_DEAD_AUTHORED_BLOCKS, KIND_BONFIRE,
                        KIND_BRAZIER, KIND_CANDLE, KIND_CHANDELIER, KIND_LAMP, KIND_TORCH, ROUTE_AUTHORED,
                        ROUTE_EMISSIVE, ROUTE_FLAME, ROUTE_NAME, ROUTE_RESTORED, M2Batch, M2Emitter, M2Light,
                        M2Model)

TORCH_BOX = ((-0.5, -0.5, 0.0), (0.5, 0.5, 2.0))
POST_BOX = ((-0.6, -0.6, 0.0), (0.6, 0.6, 4.9))
WARM_RAMP = [(1.0, 0.282, 0.0), (0.875, 0.541, 0.184), (1.0, 1.0, 1.0)]
PURPLE_RAMP = [(1.0, 1.0, 1.0), (0.565, 0.212, 1.0), (0.42, 0.0, 0.745)]
GREEN_RAMP = [(0.0, 0.988, 0.0), (0.486, 0.976, 0.51), (0.851, 1.0, 0.843)]
FLAME_TEXTURE = "ITEM\\OBJECTCOMPONENTS\\FLAMELICKSMALL.BLP"
TORCH_PATH = "World\\Generic\\Human\\Passive Doodads\\Torches\\HumanWallTorch01.m2"
STREETLAMP_PATH = "World\\Generic\\Human\\Passive Doodads\\Lamps\\StormwindStreetlamp01.m2"
FIXTURE_PATH = "World\\Generic\\Human\\Passive Doodads\\Lamps\\GoldshireFixture01.m2"
BRAZIER_PATH = "World\\Generic\\Orc\\Passive Doodads\\Braziers\\OrcBrazier01.m2"
CAMPFIRE_PATH = "World\\Generic\\Human\\Passive Doodads\\Campfire\\ElwynnCampfire.m2"
PLAIN_PATH = "World\\Generic\\Human\\Passive Doodads\\Crates\\Crate01.m2"


def model(path, lights=(), emitters=(), batches=(), bounds=TORCH_BOX):
    return M2Model(path=path, version=264, bounds_min=bounds[0], bounds_max=bounds[1], lights=list(lights),
                   emitters=list(emitters), batches=list(batches))


def point_light(position=(0.0, 0.0, 1.5), color=(0.467, 0.290, 0.133), intensity=2.0, end=8.0, visible=True,
                light_type=lr.POINT_LIGHT):
    return M2Light(light_type=light_type, bone=-1, position=position, diffuse_color=color,
                   diffuse_intensity=intensity, attenuation_start=1.0, attenuation_end=end, visible=visible)


def emitter(texture=FLAME_TEXTURE, blend=lr.PARTICLE_ADD, rate=20.0, size=0.3, colors=None, alphas=(1.0, 1.0, 1.0),
            position=(0.0, 0.3, 1.8)):
    return M2Emitter(bone=-1, position=position, texture=texture, blend=blend, emission_rate=rate,
                     colors=list(WARM_RAMP if colors is None else colors), alphas=list(alphas), sizes=[size] * 3)


def batch(texture, unlit=True, blend=0, center=(0.0, 0.0, 4.35), index_count=48):
    return M2Batch(unlit=unlit, blend=blend, texture=texture, center=center, index_count=index_count)


class Assertions(unittest.TestCase):
    def assertVector(self, actual, expected, places=3):
        self.assertEqual(len(actual), len(expected))
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e, places=places)

    def single_lamp(self, verdict, route):
        self.assertEqual(verdict.route, route)
        self.assertEqual(len(verdict.lamps), 1)
        lamp = verdict.lamps[0]
        self.assertEqual(lamp.route, route)
        return lamp


class FlameRoute(Assertions):
    def test_torch_with_a_fire_emitter_and_no_light(self):
        lamp = self.single_lamp(lr.classify(model(TORCH_PATH, emitters=[emitter()])), ROUTE_FLAME)
        self.assertEqual(lamp.kind, KIND_TORCH)
        self.assertVector(lamp.color, (1.0, 0.282, 0.0))
        self.assertEqual((lamp.intensity, lamp.reach, lamp.flags), (lr.TORCH_INTENSITY, 12.0, 0))
        self.assertVector(lamp.position, (0.0, 0.3, 1.8))

    def test_strength_tiers_and_reach_tiers(self):
        self.assertEqual(lr.fire_tier(0.09), (0.6, KIND_CANDLE))
        self.assertEqual(lr.fire_tier(0.634), (1.5, KIND_TORCH))
        self.assertEqual(lr.fire_tier(1.30), (2.0, KIND_BRAZIER))
        self.assertEqual(lr.fire_tier(3.25), (3.0, KIND_BONFIRE))
        self.assertEqual([lr.reach_for_intensity(i) for i in (0.6, 1.5, 2.0, 3.0)], [6.0, 12.0, 16.0, 24.0])
        self.assertAlmostEqual(lr.fire_strength(emitter(size=0.3, rate=16.0)), 0.6)

    def test_the_strongest_emitter_wins_and_the_first_wins_a_tie(self):
        embers = emitter(texture="X\\EMBER.BLP", size=0.08, rate=40.0, position=(0.0, 0.0, 0.5))
        flame = emitter(texture="X\\FLAMELICKLARGE.BLP", size=1.4, rate=60.0, position=(0.0, 0.0, 1.0),
                        colors=[(0.2, 0.4, 1.0)] * 3)
        twin = emitter(texture="X\\FLAMELICKLARGE.BLP", size=1.4, rate=60.0, position=(0.0, 0.0, 1.5))
        smoke = emitter(texture="X\\FIRESMOKE.BLP", blend=2, size=2.0, rate=10.0)
        bonfire = model("World\\Goober\\Bonfire.m2", emitters=[embers, flame, twin, smoke],
                        bounds=((-2.0, -2.0, 0.0), (2.0, 2.0, 3.0)))
        lamp = self.single_lamp(lr.classify(bonfire), ROUTE_FLAME)
        self.assertVector(lamp.position, (0.0, 0.0, 1.0))
        self.assertEqual((lamp.kind, lamp.intensity, lamp.reach), (KIND_BONFIRE, 3.0, 24.0))
        self.assertVector(lamp.color, lr.softened_cold_color((0.2, 0.4, 1.0)))

    def test_emitters_that_are_not_flames(self):
        self.assertTrue(lr.fire_emitter(emitter(texture="X\\CANDLEFLAME.BLP")))
        self.assertTrue(lr.fire_emitter(emitter(blend=lr.PARTICLE_NO_ALPHA_ADD)))
        self.assertTrue(lr.fire_emitter(emitter(size=0.056, rate=6.0)))
        self.assertFalse(lr.fire_emitter(emitter(texture="X\\GLOW.BLP")))
        self.assertFalse(lr.fire_emitter(emitter(texture="X\\SPELLGLOW32.BLP")))
        self.assertFalse(lr.fire_emitter(emitter(texture="X\\SMOKE01.BLP")))
        self.assertFalse(lr.fire_emitter(emitter(texture="")))
        self.assertFalse(lr.fire_emitter(emitter(texture="X\\FIRESMOKE.BLP", blend=2)))
        self.assertFalse(lr.fire_emitter(emitter(rate=0.0)))
        self.assertFalse(lr.fire_emitter(emitter(texture="X\\EMBER_OFFSET.BLP", size=0.025, rate=200.0)))
        self.assertFalse(lr.fire_emitter(emitter(alphas=(0.0, 0.0, 0.0))))
        self.assertEqual(lr.classify(model(PLAIN_PATH, emitters=[emitter(texture="X\\GLOW.BLP")])).route, None)

    def test_colour_from_the_most_saturated_visible_key(self):
        self.assertVector(lr.flame_color(emitter(colors=PURPLE_RAMP)), (0.565, 0.212, 1.0))
        self.assertVector(lr.flame_color(emitter(colors=GREEN_RAMP)), (0.0, 1.0, 0.0))
        self.assertVector(lr.flame_color(emitter(colors=WARM_RAMP)), (1.0, 0.282, 0.0))
        self.assertEqual(lr.flame_color(emitter(colors=[(1.0, 1.0, 1.0)] * 3)), lr.DEFAULT_WARM)
        burnout = [(1.0, 1.0, 1.0), (1.0, 0.6, 0.2), (1.0, 0.0, 0.0)]
        self.assertVector(lr.flame_color(emitter(colors=burnout, alphas=(1.0, 1.0, 0.0))), (1.0, 0.6, 0.2))
        self.assertVector(lr.flame_color(emitter(colors=burnout, alphas=(0.0, 0.0, 0.0))), (1.0, 0.0, 0.0))
        self.assertVector(lr.flame_color(emitter(colors=[(0.5, 0.25, 0.0)] * 3, alphas=())), (1.0, 0.5, 0.0))

    def test_cold_colours_are_softened_and_warm_ones_kept(self):
        self.assertVector(lr.softened_cold_color((0.0, 1.0, 0.0)), (0.4, 1.0, 0.4))
        purple = lr.softened_cold_color((0.565, 0.212, 1.0))
        self.assertAlmostEqual(min(purple), lr.COLD_COLOUR_FLOOR)
        self.assertAlmostEqual(max(purple), 1.0)
        self.assertGreater(purple[2], purple[0])
        self.assertGreater(purple[0], purple[1])
        self.assertEqual(lr.softened_cold_color((1.0, 0.282, 0.0)), (1.0, 0.282, 0.0))
        self.assertEqual(lr.softened_cold_color((1.0, 0.0, 0.2)), (1.0, 0.0, 0.2))
        self.assertEqual(lr.softened_cold_color((0.45, 0.65, 1.0)), (0.45, 0.65, 1.0))
        magic = self.single_lamp(lr.classify(model(TORCH_PATH, emitters=[emitter(colors=GREEN_RAMP)])),
                                 ROUTE_FLAME)
        self.assertVector(magic.color, (0.4, 1.0, 0.4))

    def test_a_far_off_flame_is_clamped_into_the_box(self):
        far = self.single_lamp(lr.classify(model(TORCH_PATH, emitters=[emitter(position=(0.2, 0.0, 50.0))])),
                               ROUTE_FLAME)
        self.assertVector(far.position, (0.2, 0.0, 2.0))
        self.assertEqual(far.flags, FLAG_CLAMPED_TO_MODEL)
        verdict = lr.classify(model(TORCH_PATH, emitters=[emitter(position=(0.2, 0.0, 50.0))]))
        self.assertIn(lr.NOTE_FLAME_CLAMPED, verdict.notes)
        near = self.single_lamp(lr.classify(model(TORCH_PATH, emitters=[emitter(position=(0.0, 0.0, 3.5))])),
                                ROUTE_FLAME)
        self.assertVector(near.position, (0.0, 0.0, 3.5))
        self.assertEqual(near.flags, 0)
        lost = self.single_lamp(lr.classify(model(TORCH_PATH, emitters=[emitter(position=(math.nan, 0.0, 1.0))])),
                                ROUTE_FLAME)
        self.assertVector(lost.position, (0.0, 0.0, 1.0))
        self.assertEqual(lost.flags, FLAG_CLAMPED_TO_MODEL)
        flat = model(TORCH_PATH, emitters=[emitter(position=(0.0, 0.0, 50.0))], bounds=((0.0,) * 3, (0.0,) * 3))
        self.assertVector(self.single_lamp(lr.classify(flat), ROUTE_FLAME).position, (0.0, 0.0, 50.0))


class NameRoutes(Assertions):
    def test_streetlamp_lights_at_its_opaque_unlit_glass(self):
        batches = [batch("X\\STREETLAMP.BLP", unlit=False, center=(0.0, 0.0, 2.0), index_count=600),
                   batch("DUNGEONS\\STORMWINDLAMPGLASS.BLP", blend=0)]
        lamp = self.single_lamp(lr.classify(model(STREETLAMP_PATH, batches=batches, bounds=POST_BOX)), ROUTE_NAME)
        self.assertVector(lamp.position, (0.0, 0.0, 4.35))
        self.assertEqual((lamp.kind, lamp.color, lamp.intensity, lamp.reach, lamp.flags),
                         (KIND_LAMP, lr.DEFAULT_LAMP, 1.5, 12.0, 0))

    def test_brazier_name_without_an_emitter_lights_at_its_unlit_glow(self):
        batches = [batch("X\\METALBOWL.BLP", unlit=False, center=(0.0, 0.0, 0.5), index_count=300),
                   batch("X\\BRAZIERCOALGLOW.BLP", blend=lr.BATCH_ADD, center=(0.0, 0.0, 1.1), index_count=24)]
        lamp = self.single_lamp(lr.classify(model(BRAZIER_PATH, batches=batches)), ROUTE_NAME)
        self.assertVector(lamp.position, (0.0, 0.0, 1.1))
        self.assertEqual((lamp.kind, lamp.color, lamp.intensity, lamp.reach),
                         (KIND_BRAZIER, lr.DEFAULT_WARM, 2.0, 16.0))

    def test_a_cold_brazier_or_torch_gets_no_box_fallback(self):
        bowl = [batch("X\\METAL01.BLP", unlit=False, center=(0.0, 0.0, 0.5))]
        self.assertEqual(lr.classify(model(BRAZIER_PATH, batches=bowl)).route, None)
        self.assertEqual(lr.classify(model("World\\Azeroth\\Elwynn\\PassiveDoodads\\NA_Torch01.m2")).route, None)

    def test_a_lamp_folder_model_with_a_glowing_unlit_batch_is_emissive(self):
        glow = batch("X\\GENERICGLOW64.BLP", blend=lr.BATCH_ALPHA, center=(0.0, 0.0, 3.2), index_count=12)
        body = batch("X\\WOOD01.BLP", unlit=False, center=(0.0, 0.0, 1.0), index_count=400)
        lamp = self.single_lamp(lr.classify(model(FIXTURE_PATH, batches=[body, glow], bounds=POST_BOX)),
                                ROUTE_EMISSIVE)
        self.assertVector(lamp.position, (0.0, 0.0, 3.2))
        self.assertEqual((lamp.kind, lamp.color, lamp.intensity, lamp.reach), (KIND_LAMP, lr.DEFAULT_WARM, 1.5, 12.0))
        outside = "World\\Expansion01\\Doodads\\Generic\\BloodElf\\Banners\\BE_Banner02.m2"
        self.assertEqual(lr.classify(model(outside, batches=[body, glow])).route, None)
        for unconvincing in (batch("X\\GENERICGLOW64.BLP", unlit=False, blend=lr.BATCH_ALPHA),
                             batch("X\\GENERICGLOW64.BLP", blend=0),
                             batch("X\\WOOD01.BLP", blend=lr.BATCH_ADD),
                             batch("X\\HAZARDLIGHTBEAM.BLP", blend=lr.BATCH_ADD)):
            self.assertEqual(lr.classify(model(FIXTURE_PATH, batches=[unconvincing])).route, None)

    def test_the_largest_glow_batch_wins_and_the_last_wins_a_tie(self):
        batches = [batch("X\\GLOW32.BLP", center=(0.0, 0.0, 3.0), index_count=6),
                   batch("X\\LAMPGLASS.BLP", center=(0.0, 0.0, 4.0), index_count=48),
                   batch("X\\LAMPGLASS.BLP", center=(0.0, 0.0, 4.5), index_count=48),
                   batch("X\\PAINT.BLP", center=(0.0, 0.0, 1.0), index_count=900)]
        lamp = self.single_lamp(lr.classify(model(STREETLAMP_PATH, batches=batches, bounds=POST_BOX)), ROUTE_NAME)
        self.assertVector(lamp.position, (0.0, 0.0, 4.5))
        plain = [batch("X\\PAINT.BLP", center=(0.0, 0.0, 1.0), index_count=900)]
        lamp = self.single_lamp(lr.classify(model(STREETLAMP_PATH, batches=plain, bounds=POST_BOX)), ROUTE_NAME)
        self.assertVector(lamp.position, (0.0, 0.0, 1.0))

    def test_a_lamp_without_batches_falls_back_to_the_top_of_its_box(self):
        path = "World\\KhazModan\\Uldaman\\PassiveDoodads\\Lamps\\UldamanLamp.m2"
        verdict = lr.classify(model(path, bounds=((-1.0, -1.0, 0.0), (1.0, 3.0, 3.0))))
        lamp = self.single_lamp(verdict, ROUTE_NAME)
        self.assertVector(lamp.position, (0.0, 1.0, 3.0))
        self.assertEqual((lamp.flags, lamp.kind, lamp.color), (FLAG_BOUNDS_FALLBACK, KIND_LAMP, lr.DEFAULT_LAMP))
        self.assertIn(lr.NOTE_BOUNDS_FALLBACK, verdict.notes)
        self.assertEqual(lr.classify(model(path, bounds=((0.0,) * 3, (0.0,) * 3))).route, None)

    def test_broken_off_and_beam_names_give_nothing(self):
        glow = [batch("X\\GLOW32.BLP", blend=lr.BATCH_ADD)]
        for path in ("World\\Generic\\Human\\Passive Doodads\\LampPosts\\DuskwoodLamppostBroken.m2",
                     "World\\KhazModan\\Uldaman\\PassiveDoodads\\Lamps\\UldamanLampAndPostBusted01.m2",
                     "World\\Generic\\PassiveDoodads\\Lights\\CandleOff01.m2",
                     "World\\Lordaeron\\WesternPlaguelands\\PassiveDoodads\\WesternPlaguelandsLampostStraightOff.m2",
                     "World\\Expansion07\\Doodads\\8du_waycrest_candlestand01_unlit.m2",
                     "World\\NoDXT\\Generic\\PassiveDoodads\\VolumetricLights\\LightShaftA.m2"):
            self.assertEqual(lr.classify(model(path, batches=glow)).route, None, path)
        self.assertFalse(lr.is_broken_or_off("World\\Generic\\Lamps\\LampOffset01.m2"))
        self.assertTrue(lr.is_broken_or_off("World\\Generic\\Lamps\\Lamp_Off_02.m2"))

    def test_only_world_scenery_takes_the_name_routes(self):
        glow = [batch("X\\GLOW32.BLP", blend=lr.BATCH_ADD)]
        for path in ("Item\\ObjectComponents\\Weapon\\Misc_1H_Lantern_A_01.m2",
                     "Creature\\Lantern\\HauntedLantern.m2"):
            self.assertEqual(lr.classify(model(path, batches=glow)).route, None, path)
        self.assertEqual(lr.classify(model("Dungeons\\Textures\\Lamp\\DungeonLamp01.m2", batches=glow)).route,
                         ROUTE_NAME)
        self.assertFalse(lr.lamp_family_ok("World\\Generic\\Spells\\Lamp01.m2"))
        self.assertTrue(lr.lamp_family_ok("world/generic/lamps/lamp01.m2"))

    def test_name_kinds_and_intensities(self):
        kinds = {"x\\KarazanChandelier_01.m2": KIND_CHANDELIER, "x\\Scholme_Candelabra.m2": KIND_CANDLE,
                 "x\\SkullCandle01.m2": KIND_CANDLE, "x\\DuskwoodLamppost.m2": KIND_LAMP,
                 "x\\GeneralHangingLantern01.m2": KIND_LAMP, "x\\AhnQirajSconce01.m2": KIND_LAMP,
                 "x\\UldamanBrazier01.m2": KIND_BRAZIER, "x\\NA_Torch01.m2": KIND_TORCH, "x\\BE_Banner02.m2": None}
        for path, kind in kinds.items():
            self.assertEqual(lr.lamp_kind(path), kind, path)
        intensities = {KIND_CHANDELIER: 2.0, KIND_CANDLE: 0.6, KIND_LAMP: 1.5, KIND_BRAZIER: 2.0, KIND_TORCH: 1.5,
                       None: 1.5}
        for kind, intensity in intensities.items():
            self.assertEqual(lr.lamp_intensity(kind), intensity)

    def test_coloured_names(self):
        colours = {"x\\StormwindStreetlamp01.m2": lr.DEFAULT_LAMP, "x\\NE_LanternBlue01.m2": (0.45, 0.65, 1.0),
                   "x\\BE_lantern_red_001.m2": (1.0, 0.35, 0.25), "x\\Scholme_GreenCandelabra.m2": (0.40, 1.0, 0.45),
                   "x\\PurpleSconce.m2": (0.70, 0.40, 1.0), "x\\ArcaneLamp01.m2": (0.70, 0.40, 1.0),
                   "x\\OrcBrazier01.m2": lr.DEFAULT_WARM, "x\\Scholme_Wax03.m2": lr.DEFAULT_WARM}
        for path, colour in colours.items():
            self.assertEqual(lr.lamp_color(path), colour, path)
        blue = "World\\Kalimdor\\Darnassus\\PassiveDoodads\\Lanterns\\NE_LanternBlue01.m2"
        lamp = self.single_lamp(lr.classify(model(blue)), ROUTE_NAME)
        self.assertEqual(lamp.color, (0.45, 0.65, 1.0))


class AuthoredLights(Assertions):
    def test_an_authored_light_becomes_one_lamp(self):
        verdict = lr.classify(model(STREETLAMP_PATH, lights=[point_light()], emitters=[emitter()], bounds=POST_BOX))
        lamp = self.single_lamp(verdict, ROUTE_AUTHORED)
        self.assertVector(lamp.color, (1.0, 0.290 / 0.467, 0.133 / 0.467))
        self.assertAlmostEqual(lamp.intensity, 0.934)
        self.assertEqual((lamp.reach, lamp.kind, lamp.flags), (8.0, KIND_LAMP, 0))
        self.assertVector(lamp.position, (0.0, 0.0, 1.5))
        self.assertEqual(verdict.notes, [])

    def test_every_emitting_point_light_counts_and_the_rest_do_not(self):
        lights = [point_light(position=(0.0, 0.0, 1.0), end=0.0), point_light(visible=False),
                  point_light(light_type=0), point_light(intensity=0.0), point_light(color=(0.004, 0.004, 0.004)),
                  point_light(position=(1.0, 0.0, 1.0), end=-3.0, intensity=1.0, color=(0.0, 0.5, 1.0))]
        verdict = lr.classify(model(CAMPFIRE_PATH, lights=lights))
        self.assertEqual(verdict.route, ROUTE_AUTHORED)
        self.assertEqual([lamp.reach for lamp in verdict.lamps], [12.0, 12.0])
        self.assertEqual([lamp.kind for lamp in verdict.lamps], [KIND_LAMP, KIND_LAMP])
        self.assertVector(verdict.lamps[1].color, (0.0, 0.5, 1.0))
        self.assertAlmostEqual(verdict.lamps[1].intensity, 1.0)
        candle = lr.classify(model("World\\Generic\\Candles\\SkullCandle01.m2", lights=[point_light()]))
        self.assertEqual(candle.lamps[0].kind, KIND_CANDLE)

    def test_dead_blocks_only(self):
        dead = [point_light(intensity=0.0), point_light(visible=False)]
        verdict = lr.classify(model(PLAIN_PATH, lights=dead))
        self.assertEqual((verdict.route, verdict.lamps, verdict.notes), (None, [], [lr.NOTE_DEAD_BLOCKS]))

    def test_dead_blocks_leave_the_flame_route_open_and_flag_it(self):
        verdict = lr.classify(model(TORCH_PATH, lights=[point_light(intensity=0.0)], emitters=[emitter()]))
        lamp = self.single_lamp(verdict, ROUTE_FLAME)
        self.assertEqual(lamp.flags, FLAG_DEAD_AUTHORED_BLOCKS)
        self.assertIn(lr.NOTE_DEAD_BLOCKS, verdict.notes)

    def test_a_live_non_point_block_keeps_the_synthesis_out(self):
        lights = [point_light(intensity=0.0), point_light(light_type=0)]
        verdict = lr.classify(model(TORCH_PATH, lights=lights, emitters=[emitter()]))
        self.assertEqual((verdict.route, verdict.lamps), (None, []))
        self.assertIn(lr.NOTE_LIVE_NON_POINT_LIGHT, verdict.notes)

    def test_non_finite_lights_do_not_emit(self):
        lights = [point_light(position=(math.nan, 0.0, 0.0)), point_light(intensity=math.inf),
                  point_light(color=(1.0, math.nan, 0.0))]
        self.assertEqual(lr.classify(model(PLAIN_PATH, lights=lights)).route, None)
        self.assertEqual(lr.classify(model(PLAIN_PATH, lights=[point_light(end=math.inf)])).lamps[0].reach, 12.0)


class RestoredLights(Assertions):
    def test_a_stock_light_is_restored_when_the_boxes_agree(self):
        stock = model(STREETLAMP_PATH, lights=[point_light(position=(0.0, 0.0, 4.4))], bounds=POST_BOX)
        top = model(STREETLAMP_PATH, bounds=((-0.7, -0.5, 0.1), (0.7, 0.7, 5.5)))
        lamp = self.single_lamp(lr.classify(top, stock), ROUTE_RESTORED)
        self.assertVector(lamp.position, (0.0, 0.0, 4.4))
        self.assertEqual((lamp.kind, lamp.reach, lamp.flags), (KIND_LAMP, 8.0, 0))
        dead_top = model(STREETLAMP_PATH, lights=[point_light(intensity=0.0)], bounds=POST_BOX)
        verdict = lr.classify(dead_top, stock)
        self.assertEqual(self.single_lamp(verdict, ROUTE_RESTORED).flags, FLAG_DEAD_AUTHORED_BLOCKS)
        self.assertEqual(verdict.notes, [lr.NOTE_DEAD_BLOCKS])

    def test_an_authored_top_light_wins_over_the_stock_one(self):
        stock = model(STREETLAMP_PATH, lights=[point_light(position=(0.0, 0.0, 4.4))], bounds=POST_BOX)
        top = model(STREETLAMP_PATH, lights=[point_light(position=(0.0, 0.0, 9.0))], bounds=POST_BOX)
        self.assertVector(self.single_lamp(lr.classify(top, stock), ROUTE_AUTHORED).position, (0.0, 0.0, 9.0))

    def test_very_different_boxes_refuse_the_restore(self):
        stock = model(PLAIN_PATH, lights=[point_light()], bounds=POST_BOX)
        scaled = model(PLAIN_PATH, bounds=((-2.4, -2.4, 0.0), (2.4, 2.4, 4.9)))
        verdict = lr.classify(scaled, stock)
        self.assertEqual((verdict.route, verdict.lamps, verdict.notes), (None, [], [lr.NOTE_BOXES_DIFFER]))
        moved = model(PLAIN_PATH, bounds=((2.4, -0.6, 0.0), (3.6, 0.6, 4.9)))
        self.assertEqual(lr.classify(moved, stock).notes, [lr.NOTE_BOXES_DIFFER])
        flattened = model(PLAIN_PATH, bounds=((-0.6, -0.6, 2.45), (0.6, 0.6, 2.45)))
        self.assertEqual(lr.classify(flattened, stock).notes, [lr.NOTE_BOXES_DIFFER])

    def test_a_refused_restore_falls_through_to_the_name_route(self):
        stock = model(STREETLAMP_PATH, lights=[point_light()], bounds=POST_BOX)
        top = model(STREETLAMP_PATH, bounds=((-3.0, -3.0, 0.0), (3.0, 3.0, 14.0)))
        verdict = lr.classify(top, stock)
        lamp = self.single_lamp(verdict, ROUTE_NAME)
        self.assertVector(lamp.position, (0.0, 0.0, 14.0))
        self.assertEqual(verdict.notes, [lr.NOTE_BOXES_DIFFER, lr.NOTE_BOUNDS_FALLBACK])

    def test_a_stock_without_emitting_lights_restores_nothing(self):
        stock = model(PLAIN_PATH, lights=[point_light(intensity=0.0)], bounds=POST_BOX)
        verdict = lr.classify(model(PLAIN_PATH, bounds=POST_BOX), stock)
        self.assertEqual((verdict.route, verdict.notes), (None, []))
        same = model(PLAIN_PATH, bounds=POST_BOX)
        self.assertEqual(lr.classify(same, same).route, None)


class SpellEffects(Assertions):
    def test_spell_paths_never_give_lamps(self):
        for path in ("Spells\\Fire_Nova_State.m2", "SPELLS\\FIREBALL_MISSILE.M2", "spells/lantern_impact.m2",
                     "Creature\\FireElemental\\Spells\\FireCore.m2"):
            verdict = lr.classify(model(path, lights=[point_light()], emitters=[emitter()],
                                        batches=[batch("X\\GLOW32.BLP", blend=lr.BATCH_ADD)]))
            self.assertEqual((verdict.route, verdict.lamps, verdict.notes), (None, [], [lr.NOTE_SPELL_EFFECT]))
        self.assertFalse(lr.is_spell_path("World\\Generic\\Passive Doodads\\SpellStone01.m2"))
        stone = lr.classify(model("World\\Generic\\Passive Doodads\\SpellStone01.m2", emitters=[emitter()]))
        self.assertEqual(stone.route, ROUTE_FLAME)

    def test_lamp_like_paths(self):
        self.assertTrue(lr.is_lamp_like(STREETLAMP_PATH))
        self.assertTrue(lr.is_lamp_like(FIXTURE_PATH))
        self.assertFalse(lr.is_lamp_like(PLAIN_PATH))
        self.assertFalse(lr.is_lamp_like("Spells\\Lantern_Impact.m2"))


if __name__ == "__main__":
    unittest.main()
