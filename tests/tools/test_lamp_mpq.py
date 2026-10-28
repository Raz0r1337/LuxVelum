import bz2
import os
import random
import struct
import tempfile
import unittest
import zlib

import lamp_mpq as mpq
from mpq_fixture import (BLOCK_COUNT_FIELD, BLOCK_POSITION_FIELD, HASH_COUNT_FIELD, MARKER_NAME, TABLE_ENTRY_SIZE,
                         FixtureFile, build_mpq, encrypt_bytes, implode, pkware_stream, with_hash_table_last,
                         with_header_words, write_marker_archive, write_mpq)

SMALL_SECTOR_SHIFT = 0
SMALL_SECTOR = 512
VERSIONS = (1, 2, 3, 4)
LOCALE_EN_US = 0x409
LOCALE_DE_DE = 0x407
EXTRA_BLOCKS = 1000
ALL_ENTRIES = 0xFFFFFFFF


def text_block(size, seed=7):
    generator = random.Random(seed)
    words = [b"lamp", b"torch", b"brazier", b"candle", b"lantern", b"glow", b"fire", b"\r\n", b" "]
    out = bytearray()
    while len(out) < size:
        out += generator.choice(words)
    return bytes(out[:size])


def noise(size, seed=11):
    generator = random.Random(seed)
    return bytes(generator.getrandbits(8) for _ in range(size))


def storage_kinds():
    text = text_block(3 * SMALL_SECTOR + 77)
    mixed = noise(SMALL_SECTOR) + bytes(SMALL_SECTOR) + noise(SMALL_SECTOR // 2, 3)
    return [
        FixtureFile("Plain\\multi.bin", text),
        FixtureFile("Plain\\unit.bin", text, single_unit=True),
        FixtureFile("Zlib\\multi.bin", text, compression="zlib"),
        FixtureFile("Zlib\\unit.bin", text, compression="zlib", single_unit=True),
        FixtureFile("Bzip2\\multi.bin", text, compression="bzip2"),
        FixtureFile("Bzip2\\unit.bin", text, compression="bzip2", single_unit=True),
        FixtureFile("Pkware\\multi.bin", text, compression="pkware"),
        FixtureFile("Implode\\binary.bin", text, compression="implode"),
        FixtureFile("Implode\\ascii.bin", text, compression="implode", implode_ascii=True, implode_dictionary_bits=4),
        FixtureFile("Implode\\unit.bin", text, compression="implode", single_unit=True, implode_dictionary_bits=5),
        FixtureFile("Crypt\\plain.bin", text, encrypted=True),
        FixtureFile("Crypt\\plain-fixed.bin", text, encrypted=True, fix_key=True),
        FixtureFile("Crypt\\zlib.bin", text, compression="zlib", encrypted=True),
        FixtureFile("Crypt\\zlib-fixed.bin", text, compression="zlib", encrypted=True, fix_key=True),
        FixtureFile("Crypt\\unit-fixed.bin", text, compression="zlib", single_unit=True, encrypted=True,
                    fix_key=True),
        FixtureFile("Crypt\\implode.bin", text, compression="implode", encrypted=True),
        FixtureFile("Crc\\zlib.bin", text, compression="zlib", sector_crc=True),
        FixtureFile("Crc\\crypt.bin", text, compression="zlib", sector_crc=True, encrypted=True, fix_key=True),
        FixtureFile("Raw\\noise.bin", noise(2 * SMALL_SECTOR + 5), compression="zlib"),
        FixtureFile("Raw\\mixed.bin", mixed, compression="zlib", encrypted=True),
        FixtureFile("Edge\\one-sector.bin", text[:SMALL_SECTOR], compression="zlib"),
        FixtureFile("Edge\\one-byte.bin", b"x", compression="zlib"),
        FixtureFile("Edge\\empty.bin", b"", compression="zlib"),
    ]


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, name, files, **options):
        path = write_mpq(os.path.join(self.root, name), files, **options)
        archive = mpq.MpqArchive(path)
        self.addCleanup(archive.close)
        return archive

    def raw_archive(self, name, data):
        path = os.path.join(self.root, name)
        with open(path, "wb") as handle:
            handle.write(data)
        archive = mpq.MpqArchive(path)
        self.addCleanup(archive.close)
        return archive


def name_in_slot(slots, wanted, taken=()):
    for index in range(1000):
        name = "f%d.txt" % index
        if mpq.mpq_name(name).index % slots in wanted and name not in taken:
            return name
    raise AssertionError("no name hashes into %s" % (wanted,))


def with_extra_blocks(archive):
    blocks = struct.unpack_from("<I", archive, BLOCK_COUNT_FIELD)[0]
    return with_header_words(archive, BLOCK_COUNT_FIELD, blocks + EXTRA_BLOCKS)


def with_block_table_beyond_the_end(archive):
    return with_header_words(archive, BLOCK_POSITION_FIELD, len(archive) + TABLE_ENTRY_SIZE)


class PkwareTests(unittest.TestCase):
    def test_public_example_decodes(self):
        self.assertEqual(mpq.explode(bytes.fromhex("00 04 82 24 25 8F 80 7F"), 13), b"AIAIAIAIAIAIA")

    def test_code_tables_match_the_published_codes(self):
        self.assertEqual(mpq.PKWARE_LENGTH_CODES[0], (0x05, 3))
        self.assertEqual(mpq.PKWARE_LENGTH_CODES[1], (0x03, 2))
        self.assertEqual(mpq.PKWARE_LENGTH_CODES[15], (0x00, 7))
        self.assertEqual(mpq.PKWARE_DISTANCE_CODES[0], (0x03, 2))
        self.assertEqual(mpq.PKWARE_DISTANCE_CODES[1], (0x0D, 4))
        self.assertEqual(mpq.PKWARE_DISTANCE_CODES[63], (0x00, 8))
        self.assertEqual(mpq.PKWARE_ASCII_CODES[0x00], (0x0490, 11))
        self.assertEqual(mpq.PKWARE_ASCII_CODES[0x20], (0x000F, 4))
        self.assertEqual(mpq.PKWARE_ASCII_CODES[ord("A")], (0x0031, 6))
        self.assertEqual(mpq.PKWARE_ASCII_CODES[ord("e")], (0x001B, 5))
        self.assertEqual(mpq.PKWARE_ASCII_CODES[0xFF], (0x0000, 13))
        self.assertEqual(mpq.PKWARE_LENGTH_BASES, (0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 14, 22, 38, 70, 134, 262))
        self.assertEqual(mpq.PKWARE_END_OF_STREAM, 519)

    def test_round_trips_every_mode_and_dictionary_size(self):
        samples = [text_block(5000), noise(700), bytes(3000), b"ab" * 900, bytes(range(256)) * 3]
        for ascii in (False, True):
            for dictionary_bits in (4, 5, 6):
                for sample in samples:
                    with self.subTest(ascii=ascii, dictionary_bits=dictionary_bits, size=len(sample)):
                        packed = implode(sample, dictionary_bits, ascii)
                        self.assertEqual(mpq.explode(packed, len(sample)), sample)

    def test_longest_repeat_and_farthest_distances(self):
        head = noise(4096, 5)
        tokens = list(head) + [(518, 4096), (2, 256), (3, 1)]
        expected = bytearray(head)
        for length, distance in ((518, 4096), (2, 256), (3, 1)):
            for _ in range(length):
                expected.append(expected[-distance])
        self.assertEqual(mpq.explode(pkware_stream(tokens, 6), len(expected)), bytes(expected))

    def test_rejects_broken_streams(self):
        cases = {
            "mode": bytes([2, 4]) + pkware_stream([65])[2:],
            "dictionary": bytes([0, 7]) + pkware_stream([65])[2:],
            "short": b"\x00\x04",
            "unterminated": pkware_stream([65, 66, 67], terminated=False),
            "before start": pkware_stream([(3, 1)]),
            "too long": pkware_stream([65, (20, 1)]),
        }
        for reason, data in cases.items():
            with self.subTest(reason=reason):
                with self.assertRaises(mpq.MpqError):
                    mpq.explode(data, 10)


class HashAndCipherTests(unittest.TestCase):
    def test_table_keys_match_storm(self):
        self.assertEqual(mpq.HASH_TABLE_KEY, 0xC3AF3770)
        self.assertEqual(mpq.BLOCK_TABLE_KEY, 0xEC83B3A3)

    def test_names_ignore_case_and_separator(self):
        upper = mpq.mpq_name("WORLD\\MAPS\\AZEROTH\\AZEROTH_32_48.ADT")
        lower = mpq.mpq_name("world/maps/azeroth/Azeroth_32_48.adt")
        self.assertEqual(upper[2:], lower[2:])
        self.assertNotEqual(upper[2:], mpq.mpq_name("world/maps/azeroth/azeroth_32_49.adt")[2:])

    def test_decryption_inverts_encryption(self):
        data = noise(1027)
        encrypted = encrypt_bytes(data, 0x12345678)
        self.assertNotEqual(encrypted[:1024], data[:1024])
        self.assertEqual(encrypted[1024:], data[1024:])
        self.assertEqual(mpq.decrypt_bytes(encrypted, 0x12345678), data)

    def test_names_hash_their_stored_bytes_and_fold_only_ascii(self):
        self.assertEqual(mpq.normalised_name("wé/x"), b"W\xe9\\X")
        self.assertEqual(mpq.normalised_name(b"w\xe9/x"), b"W\xe9\\X")
        self.assertEqual(mpq.mpq_name("Lampé.m2")[2:], mpq.mpq_name(b"LAMP\xe9.M2")[2:])
        self.assertNotEqual(mpq.mpq_name("lampé.m2")[2:], mpq.mpq_name("LAMPÉ.M2")[2:])
        self.assertEqual(mpq.mpq_name(b"w\xe9").text, "wé")
        self.assertEqual(mpq.normalised_name("lamp\u0101"), b"LAMP\xc4\x81")

    def test_file_key_uses_the_plain_name_and_fix_key(self):
        entry = mpq.MpqEntry(0x1234, 10, 100, mpq.FILE_EXISTS | mpq.FILE_ENCRYPTED, 0, 0, 0)
        fixed = entry._replace(flags=entry.flags | mpq.FILE_FIX_KEY)
        base = mpq.file_key("Some\\Folder\\file.txt", entry)
        self.assertEqual(base, mpq.file_key("FILE.TXT", entry))
        self.assertEqual(mpq.file_key("Some/Folder/file.txt", fixed), ((base + 0x1234) & 0xFFFFFFFF) ^ 100)


class MpqArchiveTests(TempDirTest):
    def test_reads_every_storage_kind_in_every_version(self):
        files = storage_kinds()
        for version in VERSIONS:
            with self.subTest(version=version):
                archive = self.archive("v%d.MPQ" % version, files, version=version, sector_shift=SMALL_SECTOR_SHIFT)
                self.assertEqual(archive.format_version, version - 1)
                self.assertEqual(archive.sector_size, SMALL_SECTOR)
                for file in files:
                    with self.subTest(file=file.name):
                        self.assertTrue(archive.has(file.name))
                        self.assertEqual(archive.read(file.name), file.data)

    def test_compressed_tables_in_versions_three_and_four(self):
        files = [FixtureFile("File%02d.txt" % index, text_block(300, index), compression="zlib") for index in range(40)]
        for version in (3, 4):
            with self.subTest(version=version):
                archive = self.archive("t%d.MPQ" % version, files, version=version, compress_tables=True,
                                       hash_table_size=128)
                self.assertLess(archive.header.hash_table_stored_size, 128 * 16)
                self.assertLess(archive.header.block_table_stored_size, 40 * 16)
                for file in files:
                    self.assertEqual(archive.read(file.name), file.data)

    def test_v1_combines_compressions_while_v2_rejects_the_combination(self):
        file = FixtureFile("Combined.txt", text_block(1500), compression="zlib+bzip2")
        self.assertEqual(self.archive("v1.MPQ", [file], version=1).read(file.name), file.data)
        with self.assertRaises(mpq.MpqUnsupported) as caught:
            self.archive("v2.MPQ", [file], version=2).read(file.name)
        self.assertEqual(caught.exception.mask, 0x12)

    def test_names_are_found_whatever_their_case_and_separator(self):
        archive = self.archive("names.MPQ", [FixtureFile("World\\Maps\\Test\\Test.wdt", b"wdt", compression="zlib")])
        self.assertEqual(archive.read("WORLD/maps/test/TEST.WDT"), b"wdt")
        self.assertEqual(archive.read(b"world\\maps\\test\\test.wdt"), b"wdt")

    def test_absent_files_give_none(self):
        archive = self.archive("absent.MPQ", [FixtureFile("here.txt", b"here")])
        self.assertFalse(archive.has("missing.txt"))
        self.assertIsNone(archive.entry("missing.txt"))
        self.assertIsNone(archive.read("missing.txt"))
        self.assertIsNone(archive.read_prefix("missing.txt", 4))

    def test_delete_marker_hides_the_file(self):
        archive = self.archive("deleted.MPQ", [FixtureFile("gone.m2", delete_marker=True)])
        self.assertTrue(archive.entry("gone.m2").deleted)
        self.assertFalse(archive.has("gone.m2"))
        self.assertIsNone(archive.read("gone.m2"))

    def test_neutral_locale_wins_else_the_first_entry(self):
        localised = [FixtureFile("Interface\\text.txt", b"us", locale=LOCALE_EN_US),
                     FixtureFile("Interface\\text.txt", b"neutral"),
                     FixtureFile("Interface\\text.txt", b"de", locale=LOCALE_DE_DE)]
        self.assertEqual(self.archive("neutral.MPQ", localised).read("interface\\text.txt"), b"neutral")
        only_localised = [localised[0], localised[2]]
        archive = self.archive("first.MPQ", only_localised)
        self.assertEqual(archive.read("interface\\text.txt"), b"us")
        self.assertEqual(archive.entry("interface\\text.txt").locale, LOCALE_EN_US)

    def test_lookup_passes_deleted_hash_slots_and_stops_on_a_full_table(self):
        archive = self.archive("tomb.MPQ", [FixtureFile("after.txt", b"found")], tombstones=["after.txt"] * 3)
        self.assertEqual(archive.read("after.txt"), b"found")
        files = [FixtureFile("full%d.txt" % index, b"%d" % index) for index in range(4)]
        full = self.archive("full.MPQ", files, hash_table_size=4)
        self.assertEqual(full.read("full3.txt"), b"3")
        self.assertIsNone(full.read("not-there.txt"))

    def test_finds_the_header_after_a_prefix_and_through_user_data(self):
        file = FixtureFile("x.txt", text_block(900), compression="zlib", encrypted=True, fix_key=True)
        for version in (1, 2):
            with self.subTest(version=version):
                shifted = self.archive("shift%d.MPQ" % version, [file], prefix_size=1536, version=version)
                self.assertEqual(shifted.header.offset, 1536)
                self.assertEqual(shifted.read("x.txt"), file.data)
                wrapped = self.archive("user%d.MPQ" % version, [file], user_data_offset=0x600, version=version)
                self.assertEqual(wrapped.header.offset, 0x600)
                self.assertEqual(wrapped.read("x.txt"), file.data)

    def test_lists_the_listfile(self):
        files = [FixtureFile("a\\one.txt", b"1"), FixtureFile("b\\two.txt", b"2")]
        self.assertEqual(self.archive("list.MPQ", files, listfile=True).listfile(), ["a\\one.txt", "b\\two.txt"])
        self.assertEqual(self.archive("nolist.MPQ", files).listfile(), [])

    def test_not_an_archive_names_the_path(self):
        path = os.path.join(self.root, "fake.MPQ")
        with open(path, "wb") as handle:
            handle.write(noise(5000))
        with self.assertRaises(mpq.MpqError) as caught:
            mpq.MpqArchive(path)
        self.assertIn("fake.MPQ", str(caught.exception))

    def test_unsupported_compressions_report_their_mask(self):
        data = bytes(2000)
        cases = [(1, 0x01), (1, 0x40), (1, 0x81), (2, 0x12), (2, 0x20), (2, 0x22), (2, 0x41), (4, 0x12)]
        for version, mask in cases:
            with self.subTest(version=version, mask=mask):
                odd = FixtureFile("odd.wav", data, forced_mask=mask)
                archive = self.archive("m%d-%02x.MPQ" % (version, mask), [odd], version=version)
                with self.assertRaises(mpq.MpqUnsupported) as caught:
                    archive.read("odd.wav")
                self.assertEqual(caught.exception.mask, mask)
                self.assertIn("odd.wav", str(caught.exception))
                self.assertIn(archive.path, str(caught.exception))

    def test_patch_files_are_unsupported(self):
        archive = self.archive("patch.MPQ", [FixtureFile("p.m2", b"data", extra_flags=mpq.FILE_PATCH_FILE)])
        with self.assertRaises(mpq.MpqUnsupported):
            archive.read("p.m2")

    def test_corrupt_data_names_archive_and_file(self):
        archive = self.archive("corrupt.MPQ", [FixtureFile("bad.m2", text_block(3000), compression="zlib",
                                                           corrupt_payload=True)])
        with self.assertRaises(mpq.MpqError) as caught:
            archive.read("bad.m2")
        self.assertNotIsInstance(caught.exception, mpq.MpqUnsupported)
        self.assertIn("bad.m2", str(caught.exception))
        self.assertIn("corrupt.MPQ", str(caught.exception))

    def test_tables_cut_off_by_the_end_of_the_file_keep_their_whole_entries(self):
        archive = self.raw_archive("cut.MPQ", build_mpq([FixtureFile("a.txt", b"a" * 100)])[:-8])
        self.assertIsNone(archive.read("a.txt"))
        self.assertEqual(archive.warnings, ["the block table is cut to 0 of 1 entries by the end of the file"])

    def test_a_block_count_beyond_the_end_of_the_file_is_cut_as_storm_does(self):
        files = [FixtureFile("f%d.txt" % index, text_block(300, index), compression="zlib") for index in range(4)]
        archive = self.raw_archive("ewix.MPQ", with_extra_blocks(build_mpq(files)))
        for file in files:
            self.assertEqual(archive.read(file.name), file.data)
        self.assertEqual(archive.warnings, ["the block table is cut to 4 of 1004 entries by the end of the file"])

    def test_a_hash_table_cut_by_the_end_of_the_file_ends_lookups_there(self):
        low = name_in_slot(16, range(0, 4))
        high = name_in_slot(16, range(12, 16))
        files = [FixtureFile(low, b"low"), FixtureFile(high, b"high")]
        whole = with_hash_table_last(build_mpq(files, hash_table_size=16))
        self.assertEqual(self.raw_archive("whole.MPQ", whole).read(high), b"high")
        archive = self.raw_archive("cut-hash.MPQ", whole[:-8 * TABLE_ENTRY_SIZE])
        self.assertEqual(archive.read(low), b"low")
        self.assertIsNone(archive.read(high))
        self.assertIsNone(archive.read(name_in_slot(16, range(8, 16), (high,))))
        self.assertEqual(archive.warnings, ["the hash table is cut to 8 of 16 entries by the end of the file"])

    def test_a_table_that_fails_to_load_fails_once_and_is_not_read_again(self):
        archive = self.raw_archive("lost.MPQ", with_block_table_beyond_the_end(build_mpq([FixtureFile("a.txt", b"a")])))
        with self.assertRaises(mpq.MpqError) as first:
            archive.read("a.txt")
        self.assertIn("the block table lies beyond the end of the file", str(first.exception))
        self.assertIn("lost.MPQ", str(first.exception))
        read_once = archive.bytes_read
        for _ in range(3):
            with self.assertRaises(mpq.MpqError) as again:
                archive.has("a.txt")
            self.assertEqual(str(again.exception), str(first.exception))
        self.assertEqual((archive.bytes_read, archive.table_loads), (read_once, 0))

    def test_an_absurd_table_count_is_an_error_not_an_allocation(self):
        files = [FixtureFile("a.bin", b"x" * 5000, compression="zlib")]
        for version in (3, 4):
            with self.subTest(version=version):
                data = with_header_words(build_mpq(files, version=version, compress_tables=True), HASH_COUNT_FIELD,
                                         ALL_ENTRIES)
                archive = self.raw_archive("absurd%d.MPQ" % version, data)
                with self.assertRaises(mpq.MpqError) as caught:
                    archive.read("a.bin")
                self.assertIn("hash table is corrupt", str(caught.exception))

    def test_decompression_stops_after_the_expected_size(self):
        for method, packer, decoder in (("zlib", zlib.compress, mpq.inflate), ("bzip2", bz2.compress, mpq.bunzip)):
            with self.subTest(method=method):
                packed = packer(bytes(100000))
                self.assertEqual(decoder(packed, 100000), bytes(100000))
                with self.assertRaises(mpq.MpqError) as caught:
                    decoder(packed, 1000)
                self.assertIn("%s data is longer than 1000 bytes" % method, str(caught.exception))
                with self.assertRaises(mpq.MpqError) as caught:
                    decoder(packer(noise(5000))[:-8], 5000)
                self.assertNotIsInstance(caught.exception, mpq.MpqUnsupported)

    def test_hi_block_table_extends_offsets(self):
        file = FixtureFile("hi.txt", text_block(700), compression="zlib")
        self.assertEqual(self.archive("hi0.MPQ", [file], version=2, hi_block={}).read("hi.txt"), file.data)
        far = self.archive("hi1.MPQ", [file], version=2, hi_block={0: 1})
        self.assertEqual(far.entry("hi.txt").offset >> 32, 1)
        with self.assertRaises(mpq.MpqError):
            far.read("hi.txt")

    def test_read_prefix_decodes_only_the_sectors_it_needs(self):
        data = text_block(10 * SMALL_SECTOR + 300)
        files = [FixtureFile("big.adt", data, compression="zlib"),
                 FixtureFile("crypt.adt", data, compression="zlib", encrypted=True, fix_key=True),
                 FixtureFile("plain.adt", data, encrypted=True),
                 FixtureFile("unit.adt", data, compression="zlib", single_unit=True)]
        archive = self.archive("prefix.MPQ", files, sector_shift=SMALL_SECTOR_SHIFT)
        for name in ("big.adt", "crypt.adt", "plain.adt"):
            with self.subTest(name=name):
                stored_size = archive.entry(name).compressed_size
                for size, sectors in ((600, 2), (SMALL_SECTOR, 1), (1, 1), (0, 0)):
                    before_sectors, before_bytes = archive.sectors_read, archive.bytes_read
                    self.assertEqual(archive.read_prefix(name, size), data[:size])
                    self.assertEqual(archive.sectors_read - before_sectors, sectors)
                    self.assertLess(archive.bytes_read - before_bytes, stored_size // 3)
        self.assertEqual(archive.read_prefix("big.adt", 10 ** 6), data)
        self.assertEqual(archive.read_prefix("unit.adt", 600), data[:600])

    def test_tables_are_loaded_once(self):
        files = [FixtureFile("f%d.txt" % index, text_block(200, index), compression="zlib") for index in range(5)]
        archive = self.archive("once.MPQ", files)
        self.assertEqual(archive.table_loads, 0)
        for _ in range(3):
            for file in files:
                archive.read(file.name)
        self.assertEqual(archive.table_loads, 1)
        before = archive.bytes_read
        archive.read("f0.txt")
        self.assertEqual(archive.bytes_read - before, archive.entry("f0.txt").compressed_size)


STOCK_ORDER = [
    "common.MPQ", "common-2.MPQ", "expansion.MPQ", "lichking.MPQ",
    "enUS/locale-enUS.MPQ", "enUS/speech-enUS.MPQ", "enUS/expansion-locale-enUS.MPQ",
    "enUS/lichking-locale-enUS.MPQ", "enUS/expansion-speech-enUS.MPQ", "enUS/lichking-speech-enUS.MPQ",
    "patch.MPQ", "patch-2.MPQ", "patch-3.MPQ",
    "enUS/patch-enUS.MPQ", "enUS/patch-enUS-2.MPQ", "enUS/patch-enUS-3.MPQ",
]
CUSTOM_ORDER = ["patch-4.MPQ", "patch-A.MPQ", "patch-z.MPQ", "enUS/patch-enUS-B.MPQ"]
STRAY_ARCHIVES = ["foo.MPQ", "enUS/base-enUS.MPQ", "patch-enUS-C.MPQ", "patch-AB.MPQ"]


class ArchiveChainTests(TempDirTest):
    def setUp(self):
        super().setUp()
        self.data = os.path.join(self.root, "Data")
        self.extra = {}

    def build(self, names=STOCK_ORDER + CUSTOM_ORDER + STRAY_ARCHIVES, extra=None):
        extra = extra or {}
        for name in names:
            write_marker_archive(os.path.join(self.data, *name.split("/")), name, extra.get(name, ()))
        with open(os.path.join(self.data, "readme.txt"), "w") as handle:
            handle.write("not an archive")

    def chain(self, **options):
        chain = mpq.ArchiveChain(self.data, **options)
        self.addCleanup(chain.close)
        return chain

    def test_orders_stock_then_custom_archives(self):
        self.build()
        chain = self.chain()
        self.assertEqual(chain.locale, "enUS")
        self.assertEqual([source.name for source in chain.sources], STOCK_ORDER + CUSTOM_ORDER)
        self.assertEqual([source.custom for source in chain.sources], [False] * 16 + [True] * 4)
        self.assertEqual(chain.ignored, ["enUS/base-enUS.MPQ", "foo.MPQ", "patch-AB.MPQ", "patch-enUS-C.MPQ"])
        sizes = [os.path.getsize(os.path.join(self.data, *source.name.split("/"))) for source in chain.sources]
        self.assertEqual([source.size for source in chain.sources], sizes)

    def test_highest_priority_archive_wins(self):
        self.build()
        chain = self.chain()
        self.assertEqual(chain.read(MARKER_NAME), b"enUS/patch-enUS-B.MPQ")
        self.assertEqual(chain.read_prefix(MARKER_NAME, 4), b"enUS")
        versions = chain.versions(MARKER_NAME)
        highest_first = list(reversed(STOCK_ORDER + CUSTOM_ORDER))
        self.assertEqual([source.name for source, _ in versions], highest_first)
        self.assertEqual([data for _, data in versions], [name.encode() for name in highest_first])
        self.assertEqual(len(chain.locate(MARKER_NAME)), 20)
        self.assertIsNone(chain.read("missing.m2"))
        self.assertEqual(chain.versions("missing.m2"), [])

    def test_archive_names_match_whatever_their_case(self):
        names = ["COMMON.mpq", "Patch.mpq", "patch-a.mpq", "Patch-5.Mpq", "ENUS/Locale-enus.mpq",
                 "ENUS/PATCH-ENUS-x.MPQ"]
        self.build(names)
        chain = self.chain()
        self.assertEqual(chain.locale, "ENUS")
        self.assertEqual([source.name for source in chain.sources],
                         ["COMMON.mpq", "ENUS/Locale-enus.mpq", "Patch.mpq", "Patch-5.Mpq", "patch-a.mpq",
                          "ENUS/PATCH-ENUS-x.MPQ"])

    def test_detects_the_locale(self):
        self.build(["common.MPQ", "deDE/locale-deDE.MPQ", "frFR/locale-frFR.MPQ", "Cache/locale-xxXX.MPQ"])
        self.assertEqual(mpq.detect_locale(self.data), "deDE")
        self.assertEqual(self.chain().ignored, ["frFR/locale-frFR.MPQ"])
        write_marker_archive(os.path.join(self.data, "enUS", "locale-enUS.MPQ"), "enUS/locale-enUS.MPQ")
        self.assertEqual(mpq.detect_locale(self.data), "enUS")
        chain = self.chain(locale="frfr")
        self.assertEqual(chain.locale, "frFR")
        self.assertEqual([source.name for source in chain.sources], ["common.MPQ", "frFR/locale-frFR.MPQ"])
        self.assertEqual(chain.read(MARKER_NAME), b"frFR/locale-frFR.MPQ")

    def test_without_a_locale_folder_only_the_root_archives_load(self):
        self.build(["common.MPQ", "patch.MPQ", "patch-9.MPQ"])
        chain = self.chain()
        self.assertIsNone(chain.locale)
        self.assertEqual([source.name for source in chain.sources], ["common.MPQ", "patch.MPQ", "patch-9.MPQ"])

    def test_order_file_replaces_the_rule(self):
        self.build()
        order = os.path.join(self.root, "order.txt")
        with open(order, "w") as handle:
            handle.write("# lowest first\n\nPATCH-Z.mpq\n  enus\\patch-enUS-B.MPQ  \ncommon.MPQ\n#patch.MPQ\nfoo.MPQ\n"
                         "enUS/locale-enUS.MPQ\n")
        chain = self.chain(order_file=order)
        self.assertEqual([(source.name, source.custom) for source in chain.sources],
                         [("patch-z.MPQ", True), ("enUS/patch-enUS-B.MPQ", True), ("common.MPQ", False),
                          ("foo.MPQ", True), ("enUS/locale-enUS.MPQ", False)])
        self.assertEqual(chain.read(MARKER_NAME), b"enUS/locale-enUS.MPQ")
        self.assertIn("patch.MPQ", chain.ignored)
        self.assertNotIn("foo.MPQ", chain.ignored)
        self.assertEqual(len(chain.ignored), 24 - 5)

    def test_order_file_errors(self):
        self.build(["common.MPQ"])
        for text, reason in (("missing.MPQ\n", "no archive"), ("common.MPQ\nCOMMON.mpq\n", "twice")):
            with self.subTest(reason=reason):
                order = os.path.join(self.root, "order.txt")
                with open(order, "w") as handle:
                    handle.write(text)
                with self.assertRaises(mpq.MpqError) as caught:
                    mpq.ArchiveChain(self.data, order_file=order)
                self.assertIn(reason, str(caught.exception))

    def test_versions_list_custom_before_stock(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        self.build(["common.MPQ", "patch.MPQ", "patch-A.MPQ"],
                   {"common.MPQ": [FixtureFile(model, b"stock", compression="zlib")],
                    "patch-A.MPQ": [FixtureFile(model, b"custom", compression="zlib", encrypted=True)]})
        chain = self.chain()
        versions = chain.versions(model.lower())
        self.assertEqual([(source.name, source.custom, data) for source, data in versions],
                         [("patch-A.MPQ", True, b"custom"), ("common.MPQ", False, b"stock")])
        self.assertEqual(chain.read(model), b"custom")
        self.assertEqual([source.name for source in chain.locate(model)], ["patch-A.MPQ", "common.MPQ"])

    def test_delete_marker_in_a_custom_patch_hides_the_stock_file(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        self.build(["common.MPQ", "patch-4.MPQ", "patch-z.MPQ"],
                   {"common.MPQ": [FixtureFile(model, b"stock")],
                    "patch-4.MPQ": [FixtureFile(model, delete_marker=True)]})
        chain = self.chain()
        self.assertIsNone(chain.read(model))
        self.assertIsNone(chain.read_prefix(model, 2))
        self.assertEqual(chain.versions(model), [])
        self.assertEqual(chain.locate(model), [])

    def test_versions_stop_at_a_delete_marker(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        self.build(["common.MPQ", "patch-4.MPQ", "patch-z.MPQ"],
                   {"common.MPQ": [FixtureFile(model, b"stock")],
                    "patch-4.MPQ": [FixtureFile(model, delete_marker=True)],
                    "patch-z.MPQ": [FixtureFile(model, b"restored")]})
        chain = self.chain()
        self.assertEqual(chain.read(model), b"restored")
        self.assertEqual([(source.name, data) for source, data in chain.versions(model)],
                         [("patch-z.MPQ", b"restored")])

    def test_empty_files_and_archives_count_as_absent(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        self.build(["common.MPQ", "patch-4.MPQ"],
                   {"common.MPQ": [FixtureFile(model, b"stock")], "patch-4.MPQ": [FixtureFile(model, b"")]})
        open(os.path.join(self.data, "patch-5.MPQ"), "wb").close()
        chain = self.chain()
        self.assertEqual(chain.read(model), b"stock")
        self.assertEqual([source.name for source, _ in chain.versions(model)], ["common.MPQ"])
        self.assertEqual([source.name for source in chain.sources], ["common.MPQ", "patch-4.MPQ"])
        self.assertIn("patch-5.MPQ", chain.ignored)

    def test_archives_that_cannot_be_opened_are_listed_and_skipped(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        self.build(["common.MPQ", "patch-4.MPQ"], {"common.MPQ": [FixtureFile(model, b"stock")],
                                                    "patch-4.MPQ": [FixtureFile(model, b"custom")]})
        with open(os.path.join(self.data, "patch-Z.MPQ"), "wb") as handle:
            handle.write(noise(4096))
        lost = with_block_table_beyond_the_end(build_mpq([FixtureFile(model, b"lost")]))
        with open(os.path.join(self.data, "patch-B.MPQ"), "wb") as handle:
            handle.write(lost)
        chain = self.chain()
        self.assertEqual([source.name for source in chain.sources], ["common.MPQ", "patch-4.MPQ"])
        self.assertEqual(chain.unreadable, [
            mpq.ArchiveNote("patch-B.MPQ", len(lost), "the block table lies beyond the end of the file"),
            mpq.ArchiveNote("patch-Z.MPQ", 4096, "no MPQ header found")])
        self.assertEqual(chain.read(model), b"custom")
        self.assertEqual([source.name for source, _ in chain.versions(model)], ["patch-4.MPQ", "common.MPQ"])

    def test_archives_with_cut_tables_are_read_and_noted(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        self.build(["common.MPQ"], {"common.MPQ": [FixtureFile(model, b"stock")]})
        cut = with_extra_blocks(build_mpq([FixtureFile(model, b"custom")]))
        with open(os.path.join(self.data, "patch-4.MPQ"), "wb") as handle:
            handle.write(cut)
        chain = self.chain()
        self.assertEqual(chain.read(model), b"custom")
        self.assertEqual(chain.unreadable, [])
        self.assertEqual(chain.malformed, [mpq.ArchiveNote(
            "patch-4.MPQ", len(cut), "the block table is cut to 1 of 1001 entries by the end of the file")])

    def test_a_version_that_cannot_be_read_stands_beside_the_others(self):
        model = "World\\Generic\\Human\\Lamp.m2"
        stock = text_block(900)
        self.build(["common.MPQ", "patch-4.MPQ", "patch-z.MPQ"],
                   {"common.MPQ": [FixtureFile(model, stock, compression="zlib")],
                    "patch-4.MPQ": [FixtureFile(model, bytes(2000), forced_mask=0x01)],
                    "patch-z.MPQ": [FixtureFile(model, b"custom")]})
        chain = self.chain()
        reads = chain.version_reads(model)
        self.assertEqual([(read.source.name, read.data) for read in reads],
                         [("patch-z.MPQ", b"custom"), ("patch-4.MPQ", None), ("common.MPQ", stock)])
        self.assertIsInstance(reads[1].error, mpq.MpqUnsupported)
        self.assertIn("compression mask 0x01", str(reads[1].error))
        self.assertEqual([read.error for read in (reads[0], reads[2])], [None, None])
        self.assertEqual(chain.read(model), b"custom")
        with self.assertRaises(mpq.MpqUnsupported):
            chain.versions(model)

    def test_a_stored_name_is_found_by_its_bytes(self):
        stored = b"World\\Generic\\Lamp\xe9.m2"
        self.build(["common.MPQ"], {"common.MPQ": [FixtureFile(stored, b"accented")]})
        chain = self.chain()
        self.assertEqual(chain.read(stored.decode("latin-1")), b"accented")
        self.assertEqual(chain.read("WORLD\\GENERIC\\LAMPé.M2"), b"accented")
        self.assertIsNone(chain.read("WORLD\\GENERIC\\LAMPÉ.M2"))

    def test_archives_stay_open_with_their_tables_cached(self):
        self.build()
        with mpq.ArchiveChain(self.data) as chain:
            for _ in range(3):
                chain.read(MARKER_NAME)
                chain.versions(MARKER_NAME)
            self.assertEqual({archive.table_loads for archive in chain.archives}, {1})
            self.assertIs(chain.name(MARKER_NAME), chain.name(MARKER_NAME))
            archives = list(chain.archives)
        for archive in archives:
            with self.assertRaises(mpq.MpqError):
                archive.read(MARKER_NAME)


if __name__ == "__main__":
    unittest.main()
