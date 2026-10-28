import bz2
import os
import re
import struct
import sys
import zlib
from array import array
from collections import namedtuple
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, Union

from lamp_types import ArchiveSource

MASK32 = 0xFFFFFFFF
WORD_SIZE = 4
WORD_TYPECODE = "I" if array("I").itemsize == WORD_SIZE else "L"
BIG_ENDIAN_HOST = sys.byteorder == "big"
HIGH_OFFSET_SHIFT = 32

MPQ_MAGIC = b"MPQ\x1a"
USER_DATA_MAGIC = b"MPQ\x1b"
MAGIC_SIZE = 4
HEADER_SEARCH_STEP = 0x200
HEADER_SEARCH_WINDOW = 0x10000
USER_DATA_FORMAT = "<4sIII"
HEADER_V1_FORMAT = "<4sIIHHIIII"
HEADER_V2_FORMAT = "<QHH"
HEADER_V3_FORMAT = "<QQQ"
HEADER_V4_FORMAT = "<QQQQQ"
HEADER_V1_SIZE = 0x20
HEADER_V2_SIZE = 0x2C
HEADER_V3_SIZE = 0x44
HEADER_V4_SIZE = 0xD0
FORMAT_V1 = 0
FORMAT_V2 = 1
FORMAT_V3 = 2
FORMAT_V4 = 3
MINIMUM_HEADER_SIZES = {FORMAT_V1: HEADER_V1_SIZE, FORMAT_V2: HEADER_V2_SIZE, FORMAT_V3: HEADER_V2_SIZE,
                        FORMAT_V4: HEADER_V4_SIZE}
SECTOR_SIZE_UNIT = 0x200
SECTOR_SHIFT_MASK = 0xFF

TABLE_ENTRY_SIZE = 16
TABLE_ENTRY_WORDS = 4
HI_BLOCK_ENTRY_SIZE = 2
HASH_ENTRY_FREE = 0xFFFFFFFF
BLOCK_INDEX_MASK = 0x0FFFFFFF
NEUTRAL_LOCALE = 0
LOCALE_MASK = 0xFFFF
PLATFORM_SHIFT = 16
PLATFORM_MASK = 0xFF

FILE_IMPLODE = 0x00000100
FILE_COMPRESS = 0x00000200
FILE_COMPRESSED = 0x0000FF00
FILE_ENCRYPTED = 0x00010000
FILE_FIX_KEY = 0x00020000
FILE_PATCH_FILE = 0x00100000
FILE_SINGLE_UNIT = 0x01000000
FILE_DELETE_MARKER = 0x02000000
FILE_SECTOR_CRC = 0x04000000
FILE_EXISTS = 0x80000000

COMPRESSION_HUFFMAN = 0x01
COMPRESSION_ZLIB = 0x02
COMPRESSION_PKWARE = 0x08
COMPRESSION_BZIP2 = 0x10
COMPRESSION_SPARSE = 0x20
COMPRESSION_ADPCM_MONO = 0x40
COMPRESSION_ADPCM_STEREO = 0x80
COMPRESSION_LZMA = 0x12
KNOWN_COMPRESSION_BITS = (COMPRESSION_HUFFMAN | COMPRESSION_ZLIB | COMPRESSION_PKWARE | COMPRESSION_BZIP2
                          | COMPRESSION_SPARSE | COMPRESSION_ADPCM_MONO | COMPRESSION_ADPCM_STEREO)

CRYPT_SEED = 0x00100001
CRYPT_MULTIPLIER = 125
CRYPT_INCREMENT = 3
CRYPT_MODULUS = 0x2AAAAB
CRYPT_HALF_SHIFT = 16
CRYPT_HALF_MASK = 0xFFFF
CRYPT_HASH_TYPES = 5
CRYPT_ROW = 0x100
BYTE_MASK = 0xFF
HASH_TABLE_INDEX = 0
HASH_NAME_A = 1
HASH_NAME_B = 2
HASH_FILE_KEY = 3
HASH_KEY_MIX = 4
HASH_SEED = 0x7FED7FED
KEY_SEED = 0xEEEEEEEE
KEY_ROTATION_LEFT = 21
KEY_ROTATION_RIGHT = 11
KEY_ROTATION_ADD = 0x11111111
SEED_SHIFT = 5
SEED_INCREMENT = 3
SECTOR_TABLE_KEY_OFFSET = 1

HASH_TABLE_NAME = "(hash table)"
BLOCK_TABLE_NAME = "(block table)"
LISTFILE_NAME = "(listfile)"
LISTFILE_SEPARATORS = re.compile(r"[\r\n;]+")
NAME_CASE_FOLD = bytes.maketrans(b"abcdefghijklmnopqrstuvwxyz/", b"ABCDEFGHIJKLMNOPQRSTUVWXYZ\\")
MPQ_PATH_SEPARATOR = b"\\"
STORED_NAME_ENCODING = "latin-1"
TYPED_NAME_ENCODING = "utf-8"

PKWARE_BINARY = 0
PKWARE_ASCII = 1
PKWARE_HEADER_SIZE = 2
PKWARE_MIN_DICTIONARY_BITS = 4
PKWARE_MAX_DICTIONARY_BITS = 6
PKWARE_MIN_REPEAT = 2
PKWARE_SHORT_REPEAT_DISTANCE_BITS = 2
PKWARE_LITERAL_BITS = 8
PKWARE_LOOKUP_BITS = 8
PKWARE_ASCII_LOOKUP_BITS = 13
PKWARE_LENGTH_CODE_BITS = (3, 2, 3, 3, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 7, 7)
PKWARE_LENGTH_EXTRA_BITS = (0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8)
PKWARE_DISTANCE_CODE_RUNS = ((2, 1), (4, 2), (5, 4), (6, 15), (7, 26), (8, 16))
PKWARE_ASCII_CODE_BITS = (
    "bcccccccc87cc7ccccccccccccdccccc4a8caca87789767876777787788cb79b"
    "c676657886b967667b66679899b8b9c8c566656665b756556a55558788abbccc"
    "ddddddddddddddddddddddddddddddddddddddddddddddddcccccccccccccccc"
    "ccccccccccccccccccccccccccccccccdcdddcdddcddddcdddcccddddddddddd")

STOCK_BASE_ARCHIVES = ("common.MPQ", "common-2.MPQ", "expansion.MPQ", "lichking.MPQ")
STOCK_LOCALE_ARCHIVES = ("locale-%s.MPQ", "speech-%s.MPQ", "expansion-locale-%s.MPQ", "lichking-locale-%s.MPQ",
                         "expansion-speech-%s.MPQ", "lichking-speech-%s.MPQ")
STOCK_PATCH_ARCHIVES = ("patch.MPQ", "patch-2.MPQ", "patch-3.MPQ")
STOCK_LOCALE_PATCH_ARCHIVES = ("patch-%s.MPQ", "patch-%s-2.MPQ", "patch-%s-3.MPQ")
STOCK_PATCH_SUFFIXES = ("2", "3")
CUSTOM_PATCH_TEMPLATE = r"patch-%s([0-9a-z])\.mpq\Z"
CUSTOM_LOCALE_INFIX = "%s-"
STOCK_ARCHIVE_NAME = re.compile(
    r"(common|common-2|expansion|lichking|patch|patch-2|patch-3"
    r"|(locale|speech|expansion-locale|lichking-locale|expansion-speech|lichking-speech)-[a-z]{4}"
    r"|patch-[a-z]{4}(-[23])?)\.mpq\Z", re.IGNORECASE)
LOCALE_ARCHIVE_TEMPLATE = "locale-%s.mpq"
PREFERRED_LOCALE = "enus"
ARCHIVE_EXTENSION = ".mpq"
ORDER_FILE_COMMENT = "#"
ORDER_PATH_SEPARATORS = re.compile(r"[\\/]+")
SOURCE_PATH_SEPARATOR = "/"
CONTEXT_SEPARATOR = ": "


class MpqError(Exception):
    pass


class MpqUnsupported(MpqError):
    def __init__(self, message, mask=None):
        super().__init__(message)
        self.mask = mask


def with_context(error: MpqError, context: str) -> MpqError:
    text = context + CONTEXT_SEPARATOR + str(error)
    if isinstance(error, MpqUnsupported):
        return MpqUnsupported(text, error.mask)
    return MpqError(text)


def build_crypt_table():
    table = [0] * (CRYPT_HASH_TYPES * CRYPT_ROW)
    seed = CRYPT_SEED
    for column in range(CRYPT_ROW):
        for hash_type in range(CRYPT_HASH_TYPES):
            seed = (seed * CRYPT_MULTIPLIER + CRYPT_INCREMENT) % CRYPT_MODULUS
            high = (seed & CRYPT_HALF_MASK) << CRYPT_HALF_SHIFT
            seed = (seed * CRYPT_MULTIPLIER + CRYPT_INCREMENT) % CRYPT_MODULUS
            table[hash_type * CRYPT_ROW + column] = high | (seed & CRYPT_HALF_MASK)
    return table


CRYPT_TABLE = build_crypt_table()
KEY_MIX = CRYPT_TABLE[HASH_KEY_MIX * CRYPT_ROW:(HASH_KEY_MIX + 1) * CRYPT_ROW]


def name_bytes(name: str) -> bytes:
    try:
        return name.encode(STORED_NAME_ENCODING)
    except UnicodeEncodeError:
        return name.encode(TYPED_NAME_ENCODING)


def normalised_name(name: Union[str, bytes]) -> bytes:
    raw = name if isinstance(name, bytes) else name_bytes(name)
    return raw.translate(NAME_CASE_FOLD)


def hash_name(normalised: bytes, hash_type: int) -> int:
    table = CRYPT_TABLE
    offset = hash_type * CRYPT_ROW
    seed1 = HASH_SEED
    seed2 = KEY_SEED
    for character in normalised:
        seed1 = table[offset + character] ^ ((seed1 + seed2) & MASK32)
        seed2 = (character + seed1 + seed2 + (seed2 << SEED_SHIFT) + SEED_INCREMENT) & MASK32
    return seed1


HASH_TABLE_KEY = hash_name(normalised_name(HASH_TABLE_NAME), HASH_FILE_KEY)
BLOCK_TABLE_KEY = hash_name(normalised_name(BLOCK_TABLE_NAME), HASH_FILE_KEY)


def decrypt_words(words: array, key: int) -> None:
    mix = KEY_MIX
    seed = KEY_SEED
    for index in range(len(words)):
        seed = (seed + mix[key & BYTE_MASK]) & MASK32
        value = words[index] ^ ((key + seed) & MASK32)
        words[index] = value
        key = ((((key ^ MASK32) << KEY_ROTATION_LEFT) + KEY_ROTATION_ADD) & MASK32) | (key >> KEY_ROTATION_RIGHT)
        seed = (value + seed + (seed << SEED_SHIFT) + SEED_INCREMENT) & MASK32


def words_of(data: bytes) -> array:
    words = array(WORD_TYPECODE)
    words.frombytes(data[:len(data) - len(data) % WORD_SIZE])
    if BIG_ENDIAN_HOST:
        words.byteswap()
    return words


def bytes_of(words: array) -> bytes:
    if BIG_ENDIAN_HOST:
        swapped = array(WORD_TYPECODE, words)
        swapped.byteswap()
        return swapped.tobytes()
    return words.tobytes()


def decrypt_bytes(data: bytes, key: int) -> bytes:
    words = words_of(data)
    decrypt_words(words, key)
    return bytes_of(words) + data[len(words) * WORD_SIZE:]


MpqName = namedtuple("MpqName", ("text", "normalised", "index", "name_a", "name_b"))


def mpq_name(name: Union[str, bytes, MpqName]) -> MpqName:
    if isinstance(name, MpqName):
        return name
    normalised = normalised_name(name)
    text = name.decode(STORED_NAME_ENCODING) if isinstance(name, bytes) else name
    return MpqName(text, normalised, hash_name(normalised, HASH_TABLE_INDEX), hash_name(normalised, HASH_NAME_A),
                   hash_name(normalised, HASH_NAME_B))


class MpqEntry(namedtuple("MpqEntry", ("offset", "compressed_size", "size", "flags", "locale", "platform",
                                       "block_index"))):
    __slots__ = ()

    @property
    def deleted(self):
        return bool(self.flags & FILE_DELETE_MARKER)


def file_key(name: Union[str, bytes, MpqName], entry: MpqEntry) -> int:
    normalised = mpq_name(name).normalised
    plain = normalised[normalised.rfind(MPQ_PATH_SEPARATOR) + 1:]
    key = hash_name(plain, HASH_FILE_KEY)
    if entry.flags & FILE_FIX_KEY:
        key = ((key + entry.offset) & MASK32) ^ entry.size
    return key


def prefix_code_patterns(bit_lengths):
    order = sorted(range(len(bit_lengths)), key=lambda symbol: (bit_lengths[symbol], symbol))
    patterns = [(0, 0)] * len(bit_lengths)
    code = -1
    previous = bit_lengths[order[0]]
    for symbol in order:
        width = bit_lengths[symbol]
        code = (code + 1) << (width - previous)
        previous = width
        inverted = code ^ ((1 << width) - 1)
        stream_order = int(format(inverted, "0%db" % width)[::-1], 2)
        patterns[symbol] = (stream_order, width)
    return patterns


def expanded_runs(runs):
    return [width for width, count in runs for _ in range(count)]


def length_bases(extra_bits):
    bases = [0]
    for extra in extra_bits[:-1]:
        bases.append(bases[-1] + (1 << extra))
    return tuple(bases)


def decoding_table(patterns, lookup_bits):
    table = [None] * (1 << lookup_bits)
    for symbol, (pattern, width) in enumerate(patterns):
        for extension in range(1 << (lookup_bits - width)):
            table[pattern | (extension << width)] = (symbol, width)
    return table


PKWARE_LENGTH_CODES = prefix_code_patterns(PKWARE_LENGTH_CODE_BITS)
PKWARE_DISTANCE_CODES = prefix_code_patterns(expanded_runs(PKWARE_DISTANCE_CODE_RUNS))
PKWARE_ASCII_CODES = prefix_code_patterns([int(digit, 16) for digit in PKWARE_ASCII_CODE_BITS])
PKWARE_LENGTH_BASES = length_bases(PKWARE_LENGTH_EXTRA_BITS)
PKWARE_END_OF_STREAM = PKWARE_LENGTH_BASES[-1] + (1 << PKWARE_LENGTH_EXTRA_BITS[-1]) - 1 + PKWARE_MIN_REPEAT
PKWARE_LENGTH_TABLE = decoding_table(PKWARE_LENGTH_CODES, PKWARE_LOOKUP_BITS)
PKWARE_DISTANCE_TABLE = decoding_table(PKWARE_DISTANCE_CODES, PKWARE_LOOKUP_BITS)
PKWARE_ASCII_TABLE = decoding_table(PKWARE_ASCII_CODES, PKWARE_ASCII_LOOKUP_BITS)


class LsbBitReader:
    __slots__ = ("data", "position", "buffer", "count", "remaining")

    def __init__(self, data, start):
        self.data = data
        self.position = start
        self.buffer = 0
        self.count = 0
        self.remaining = 8 * (len(data) - start)

    def fill(self, width):
        while self.count < width:
            if self.position < len(self.data):
                self.buffer |= self.data[self.position] << self.count
            self.position += 1
            self.count += 8

    def peek(self, width):
        self.fill(width)
        return self.buffer & ((1 << width) - 1)

    def skip(self, width):
        self.remaining -= width
        if self.remaining < 0:
            raise MpqError("imploded data ends before its end marker")
        self.fill(width)
        self.buffer >>= width
        self.count -= width

    def take(self, width):
        value = self.peek(width)
        self.skip(width)
        return value


def copy_repeat(output, distance, length):
    if distance > len(output):
        raise MpqError("imploded data repeats from before its start")
    start = len(output) - distance
    if distance >= length:
        output += output[start:start + length]
    else:
        period = output[start:]
        output += (period * (length // distance + 1))[:length]


def explode(data: bytes, expected_size: int) -> bytes:
    if len(data) <= PKWARE_HEADER_SIZE:
        raise MpqError("imploded data is too short")
    mode, dictionary_bits = data[0], data[1]
    if mode not in (PKWARE_BINARY, PKWARE_ASCII):
        raise MpqError("imploded data has the unknown mode %d" % mode)
    if not PKWARE_MIN_DICTIONARY_BITS <= dictionary_bits <= PKWARE_MAX_DICTIONARY_BITS:
        raise MpqError("imploded data has the invalid dictionary size %d" % dictionary_bits)
    bits = LsbBitReader(data, PKWARE_HEADER_SIZE)
    output = bytearray()
    while True:
        if bits.take(1):
            symbol, width = PKWARE_LENGTH_TABLE[bits.peek(PKWARE_LOOKUP_BITS)]
            bits.skip(width)
            length = PKWARE_LENGTH_BASES[symbol] + bits.take(PKWARE_LENGTH_EXTRA_BITS[symbol]) + PKWARE_MIN_REPEAT
            if length == PKWARE_END_OF_STREAM:
                break
            distance_symbol, width = PKWARE_DISTANCE_TABLE[bits.peek(PKWARE_LOOKUP_BITS)]
            bits.skip(width)
            low_bits = PKWARE_SHORT_REPEAT_DISTANCE_BITS if length == PKWARE_MIN_REPEAT else dictionary_bits
            copy_repeat(output, ((distance_symbol << low_bits) | bits.take(low_bits)) + 1, length)
        elif mode == PKWARE_BINARY:
            output.append(bits.take(PKWARE_LITERAL_BITS))
        else:
            symbol, width = PKWARE_ASCII_TABLE[bits.peek(PKWARE_ASCII_LOOKUP_BITS)]
            bits.skip(width)
            output.append(symbol)
        if len(output) > expected_size:
            raise MpqError("imploded data is longer than %d bytes" % expected_size)
    return bytes(output)


def capped_output(decompressor, data, expected_size, method):
    output = decompressor.decompress(data, min(expected_size + 1, sys.maxsize))
    if len(output) > expected_size:
        raise MpqError("%s data is longer than %d bytes" % (method, expected_size))
    if not decompressor.eof:
        raise MpqError("%s data ends before its end of stream" % method)
    return output


def inflate(data, expected_size):
    try:
        return capped_output(zlib.decompressobj(), data, expected_size, "zlib")
    except zlib.error as error:
        raise MpqError("zlib data is corrupt (%s)" % error) from None


def bunzip(data, expected_size):
    try:
        return capped_output(bz2.BZ2Decompressor(), data, expected_size, "bzip2")
    except (OSError, ValueError, EOFError) as error:
        raise MpqError("bzip2 data is corrupt (%s)" % error) from None


SINGLE_METHOD_DECODERS = {COMPRESSION_ZLIB: inflate, COMPRESSION_PKWARE: explode, COMPRESSION_BZIP2: bunzip}
COMBINED_METHOD_ORDER = ((COMPRESSION_BZIP2, bunzip), (COMPRESSION_PKWARE, explode), (COMPRESSION_ZLIB, inflate))
SUPPORTED_COMBINED_BITS = COMPRESSION_BZIP2 | COMPRESSION_PKWARE | COMPRESSION_ZLIB


def unsupported_compression(mask):
    if mask & ~KNOWN_COMPRESSION_BITS or mask == 0:
        return MpqError("compression mask 0x%02X is invalid" % mask)
    return MpqUnsupported("compression mask 0x%02X is not supported" % mask, mask)


def compression_steps(mask, format_version):
    if format_version >= FORMAT_V2:
        decoder = SINGLE_METHOD_DECODERS.get(mask)
        if decoder is None:
            raise unsupported_compression(mask)
        return [decoder]
    if mask == 0 or mask & ~SUPPORTED_COMBINED_BITS:
        raise unsupported_compression(mask)
    return [decoder for bit, decoder in COMBINED_METHOD_ORDER if mask & bit]


def decompress_masked(data: bytes, expected_size: int, format_version: int) -> bytes:
    if len(data) == expected_size:
        return data
    if not data:
        raise MpqError("compressed data is empty")
    payload = data[1:]
    for decoder in compression_steps(data[0], format_version):
        payload = decoder(payload, expected_size)
    if len(payload) != expected_size:
        raise MpqError("data decompressed to %d bytes instead of %d" % (len(payload), expected_size))
    return payload


def decompress_imploded(data: bytes, expected_size: int) -> bytes:
    if len(data) == expected_size:
        return data
    result = explode(data, expected_size)
    if len(result) != expected_size:
        raise MpqError("data exploded to %d bytes instead of %d" % (len(result), expected_size))
    return result


@dataclass
class MpqHeader:
    offset: int
    format_version: int
    header_size: int
    archive_size: int
    sector_size: int
    hash_table_position: int
    block_table_position: int
    hi_block_table_position: int
    hash_table_entries: int
    block_table_entries: int
    hash_table_stored_size: int
    block_table_stored_size: int


def effective_format_version(version, header_size):
    if version == FORMAT_V2 and header_size == HEADER_V2_SIZE:
        return FORMAT_V2
    if version in (FORMAT_V3, FORMAT_V4):
        return version
    return FORMAT_V1


def v2_block_table_stored_size(header, file_size):
    if header.hi_block_table_position:
        if header.hi_block_table_position > header.block_table_position:
            return header.hi_block_table_position - header.block_table_position
        return header.block_table_stored_size
    remaining = file_size - header.offset
    if header.block_table_position >> HIGH_OFFSET_SHIFT or remaining >> HIGH_OFFSET_SHIFT:
        return header.block_table_stored_size
    if header.archive_size == remaining:
        return header.archive_size - header.block_table_position
    return header.block_table_stored_size


def apply_v2_table_sizes(header, file_size):
    if header.block_table_position >= header.hash_table_position:
        header.hash_table_stored_size = header.block_table_position - header.hash_table_position
        header.block_table_stored_size = v2_block_table_stored_size(header, file_size)


def apply_v3_table_sizes(header, archive_size64, file_size):
    limit = archive_size64
    if header.hi_block_table_position:
        if header.hi_block_table_position > file_size:
            raise MpqError("the hi-block table lies beyond the end of the file")
        limit = header.hi_block_table_position
    if header.block_table_position and header.block_table_entries:
        if header.block_table_position >= limit:
            raise MpqError("the block table lies beyond the end of the archive")
        header.block_table_stored_size = limit - header.block_table_position
        limit = header.block_table_position
    if header.hash_table_position and header.hash_table_entries:
        if header.hash_table_position >= limit:
            raise MpqError("the hash table lies beyond the end of the archive")
        header.hash_table_stored_size = limit - header.hash_table_position


def apply_v4_table_sizes(header, raw):
    hash_size, block_size, _, _, _ = struct.unpack_from(HEADER_V4_FORMAT, raw, HEADER_V3_SIZE)
    if hash_size:
        header.hash_table_stored_size = hash_size
    if block_size:
        header.block_table_stored_size = block_size


def parse_header(raw: bytes, offset: int, file_size: int) -> MpqHeader:
    (_, header_size, archive_size, version, sector_shift, hash_position, block_position, hash_entries,
     block_entries) = struct.unpack_from(HEADER_V1_FORMAT, raw)
    version = effective_format_version(version, header_size)
    if len(raw) < MINIMUM_HEADER_SIZES[version]:
        raise MpqError("the MPQ header is cut off by the end of the file")
    sector_size = SECTOR_SIZE_UNIT << (sector_shift & SECTOR_SHIFT_MASK)
    header = MpqHeader(offset, version, header_size, archive_size, sector_size, hash_position, block_position, 0,
                       hash_entries, block_entries, hash_entries * TABLE_ENTRY_SIZE, block_entries * TABLE_ENTRY_SIZE)
    if version == FORMAT_V1:
        return header
    hi_block_position, hash_high, block_high = struct.unpack_from(HEADER_V2_FORMAT, raw, HEADER_V1_SIZE)
    header.hi_block_table_position = hi_block_position
    header.hash_table_position |= hash_high << HIGH_OFFSET_SHIFT
    header.block_table_position |= block_high << HIGH_OFFSET_SHIFT
    if version == FORMAT_V2:
        if hi_block_position > file_size:
            raise MpqError("the hi-block table lies beyond the end of the file")
        apply_v2_table_sizes(header, file_size)
        return header
    archive_size64, _, het_position = archive_size, 0, 0
    if header_size >= HEADER_V3_SIZE and len(raw) >= HEADER_V3_SIZE:
        archive_size64, _, het_position = struct.unpack_from(HEADER_V3_FORMAT, raw, HEADER_V2_SIZE)
    if het_position and not hash_entries:
        raise MpqUnsupported("the archive has only HET and BET tables")
    if version == FORMAT_V3:
        apply_v3_table_sizes(header, archive_size64, file_size)
    else:
        apply_v4_table_sizes(header, raw)
    return header


class MpqArchive:
    def __init__(self, path: str):
        self.path = path
        self.label = path
        self.bytes_read = 0
        self.sectors_read = 0
        self.table_loads = 0
        self._handle = open(path, "rb")
        try:
            self.size = os.fstat(self._handle.fileno()).st_size
            self.header = self._find_header()
        except MpqError as error:
            self._handle.close()
            raise with_context(error, self.label) from None
        except BaseException:
            self._handle.close()
            raise
        self.format_version = self.header.format_version
        self.sector_size = self.header.sector_size
        self.warnings: List[str] = []
        self._hash_words = None
        self._hash_present = 0
        self._block_words = None
        self._block_count = 0
        self._hi_blocks = None
        self._table_error = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def _read_at(self, position, size):
        if size <= 0:
            return b""
        if self._handle is None:
            raise MpqError("the archive is closed")
        if position < 0 or position + size > self.size:
            raise MpqError("%d bytes at 0x%X lie beyond the end of the file" % (size, position))
        self._handle.seek(position)
        data = self._handle.read(size)
        if len(data) != size:
            raise MpqError("the file ended while reading 0x%X" % position)
        self.bytes_read += size
        return data

    def _find_header(self):
        window_start, window = 0, b""
        position = 0
        followed_user_data = False
        while position + HEADER_V1_SIZE <= self.size:
            if position < window_start or position + MAGIC_SIZE > window_start + len(window):
                window_start = position
                window = self._read_at(position, min(HEADER_SEARCH_WINDOW, self.size - position))
            magic = window[position - window_start:position - window_start + MAGIC_SIZE]
            if magic == MPQ_MAGIC:
                raw = self._read_at(position, min(HEADER_V4_SIZE, self.size - position))
                return parse_header(raw, position, self.size)
            if magic == USER_DATA_MAGIC and not followed_user_data:
                header_offset = self._user_data_header_offset(position)
                if header_offset:
                    followed_user_data = True
                    position += header_offset
                    continue
            position += HEADER_SEARCH_STEP
        raise MpqError("no MPQ header found")

    def _user_data_header_offset(self, position):
        if position + struct.calcsize(USER_DATA_FORMAT) > self.size:
            return 0
        _, data_size, header_offset, data_header_size = struct.unpack(
            USER_DATA_FORMAT, self._read_at(position, struct.calcsize(USER_DATA_FORMAT)))
        if data_size > header_offset or data_header_size > data_size or position + header_offset >= self.size:
            return 0
        return header_offset

    def _absolute(self, mpq_offset):
        if self.format_version == FORMAT_V1:
            return (self.header.offset + mpq_offset) & MASK32
        return self.header.offset + mpq_offset

    def _entries_before_the_end(self, start, entries, title):
        if start >= self.size:
            raise MpqError("the %s lies beyond the end of the file" % title)
        present = min(entries, (self.size - start) // TABLE_ENTRY_SIZE)
        if present < entries:
            self.warnings.append("the %s is cut to %d of %d entries by the end of the file"
                                 % (title, present, entries))
        return present

    def _load_compressed_table(self, start, size, stored_size, key, title):
        if start + stored_size > self.size:
            raise MpqError("the %s lies beyond the end of the file" % title)
        raw = self._read_at(start, stored_size)
        try:
            table = decompress_masked(decrypt_bytes(raw, key), size, FORMAT_V2)
        except MpqError as error:
            raise with_context(error, "the %s is corrupt" % title) from None
        return words_of(table)

    def _load_table(self, position, entries, stored_size, key, title):
        if entries == 0:
            return array(WORD_TYPECODE), 0
        size = entries * TABLE_ENTRY_SIZE
        start = self._absolute(position)
        if 0 < stored_size < size:
            return self._load_compressed_table(start, size, stored_size, key, title), entries
        present = self._entries_before_the_end(start, entries, title)
        words = words_of(self._read_at(start, present * TABLE_ENTRY_SIZE))
        decrypt_words(words, key)
        return words, present

    def load_tables(self) -> None:
        if self._hash_words is not None:
            return
        if self._table_error is not None:
            raise self._table_error.with_traceback(None) from None
        try:
            self._load_tables()
        except MpqError as error:
            self._table_error = with_context(error, self.label)
            raise self._table_error from None

    def _load_tables(self):
        header = self.header
        hash_words, hash_present = self._load_table(header.hash_table_position, header.hash_table_entries,
                                                    header.hash_table_stored_size, HASH_TABLE_KEY, "hash table")
        block_words, block_count = self._load_table(header.block_table_position, header.block_table_entries,
                                                    header.block_table_stored_size, BLOCK_TABLE_KEY, "block table")
        hi_blocks = None
        if header.format_version >= FORMAT_V2 and header.hi_block_table_position and block_count:
            start = self._absolute(header.hi_block_table_position)
            hi_blocks = struct.unpack("<%dH" % block_count, self._read_at(start, block_count * HI_BLOCK_ENTRY_SIZE))
        self._hash_words = hash_words
        self._hash_present = hash_present
        self._block_words = block_words
        self._block_count = block_count
        self._hi_blocks = hi_blocks
        self.table_loads += 1

    def _block(self, block_index, locale, platform):
        base = block_index * TABLE_ENTRY_WORDS
        words = self._block_words
        flags = words[base + 3]
        if not flags & FILE_EXISTS:
            return None
        offset = words[base]
        if self._hi_blocks is not None:
            offset |= self._hi_blocks[block_index] << HIGH_OFFSET_SHIFT
        return MpqEntry(offset, words[base + 1], words[base + 2], flags, locale, platform, block_index)

    def entry(self, name: Union[str, bytes, MpqName]) -> Optional[MpqEntry]:
        key = mpq_name(name)
        self.load_tables()
        table = self._hash_words
        entries = self.header.hash_table_entries
        if not entries:
            return None
        present = self._hash_present
        blocks = self._block_count
        mask = entries - 1
        start = index = key.index & mask
        first = None
        while index < present:
            base = index * TABLE_ENTRY_WORDS
            block = table[base + 3]
            if block == HASH_ENTRY_FREE:
                break
            if table[base] == key.name_a and table[base + 1] == key.name_b and (block & BLOCK_INDEX_MASK) < blocks:
                locale_platform = table[base + 2]
                locale = locale_platform & LOCALE_MASK
                candidate = self._block(block & BLOCK_INDEX_MASK, locale,
                                        (locale_platform >> PLATFORM_SHIFT) & PLATFORM_MASK)
                if candidate is not None:
                    if locale == NEUTRAL_LOCALE:
                        return candidate
                    if first is None:
                        first = candidate
            index = (index + 1) & mask
            if index == start:
                break
        return first

    def has(self, name: Union[str, bytes, MpqName]) -> bool:
        found = self.entry(name)
        return found is not None and not found.deleted

    def read(self, name: Union[str, bytes, MpqName]) -> Optional[bytes]:
        key = mpq_name(name)
        found = self.entry(key)
        if found is None or found.deleted:
            return None
        return self.read_entry(key, found)

    def read_prefix(self, name: Union[str, bytes, MpqName], size: int) -> Optional[bytes]:
        key = mpq_name(name)
        found = self.entry(key)
        if found is None or found.deleted:
            return None
        return self.read_entry(key, found, size)

    def listfile(self) -> List[str]:
        data = self.read(LISTFILE_NAME)
        if not data:
            return []
        return [name for name in LISTFILE_SEPARATORS.split(data.decode(STORED_NAME_ENCODING)) if name]

    def read_entry(self, name: Union[str, bytes, MpqName], found: MpqEntry, limit: Optional[int] = None) -> bytes:
        key = mpq_name(name)
        try:
            return self._read_entry(key, found, limit)
        except MpqError as error:
            raise with_context(error, "%s: %s" % (self.label, key.text)) from None

    def _read_entry(self, key, found, limit):
        if found.deleted:
            raise MpqError("the file is a deletion marker")
        if found.flags & FILE_PATCH_FILE:
            raise MpqUnsupported("incremental patch files are not supported")
        wanted = found.size if limit is None else max(0, min(limit, found.size))
        if wanted == 0:
            return b""
        encryption_key = file_key(key, found) if found.flags & FILE_ENCRYPTED else None
        start = self._absolute(found.offset)
        if found.flags & FILE_SINGLE_UNIT:
            return self._read_single_unit(found, start, encryption_key)[:wanted]
        if found.flags & FILE_COMPRESSED:
            return self._read_compressed_sectors(found, start, encryption_key, wanted)
        return self._read_plain_sectors(found, start, encryption_key, wanted)

    def _read_single_unit(self, found, start, encryption_key):
        compressed = found.flags & FILE_COMPRESSED
        raw = self._read_at(start, found.compressed_size if compressed else found.size)
        if encryption_key is not None:
            raw = decrypt_bytes(raw, encryption_key)
        self.sectors_read += 1
        if found.flags & FILE_COMPRESS:
            return decompress_masked(raw, found.size, self.format_version)
        if found.flags & FILE_IMPLODE:
            return decompress_imploded(raw, found.size)
        return raw

    def _sector_offsets(self, found, start, encryption_key, count):
        raw = self._read_at(start, (count + 1) * WORD_SIZE)
        offsets = words_of(raw)
        if encryption_key is not None:
            decrypt_words(offsets, (encryption_key - SECTOR_TABLE_KEY_OFFSET) & MASK32)
        for index in range(count):
            if offsets[index + 1] < offsets[index] or offsets[index + 1] - offsets[index] > self.sector_size:
                raise MpqError("the sector offset table is corrupt")
        return offsets

    def _decode_sector(self, found, raw, index, expected, encryption_key):
        if encryption_key is not None:
            raw = decrypt_bytes(raw, (encryption_key + index) & MASK32)
        self.sectors_read += 1
        if len(raw) >= expected:
            return raw[:expected]
        if not raw:
            return bytes(expected)
        if found.flags & FILE_COMPRESS:
            return decompress_masked(raw, expected, self.format_version)
        return decompress_imploded(raw, expected)

    def _read_compressed_sectors(self, found, start, encryption_key, wanted):
        sector_size = self.sector_size
        needed = (wanted + sector_size - 1) // sector_size
        offsets = self._sector_offsets(found, start, encryption_key, needed)
        raw = self._read_at(start + offsets[0], offsets[needed] - offsets[0])
        parts = []
        for index in range(needed):
            expected = min(sector_size, found.size - index * sector_size)
            chunk = raw[offsets[index] - offsets[0]:offsets[index + 1] - offsets[0]]
            parts.append(self._decode_sector(found, chunk, index, expected, encryption_key))
        return b"".join(parts)[:wanted]

    def _read_plain_sectors(self, found, start, encryption_key, wanted):
        sector_size = self.sector_size
        if encryption_key is None:
            self.sectors_read += (wanted + sector_size - 1) // sector_size
            return self._read_at(start, wanted)
        needed = (wanted + sector_size - 1) // sector_size
        raw = self._read_at(start, min(needed * sector_size, found.size))
        parts = [decrypt_bytes(raw[index * sector_size:(index + 1) * sector_size], (encryption_key + index) & MASK32)
                 for index in range(needed)]
        self.sectors_read += needed
        return b"".join(parts)[:wanted]


def files_by_lower_name(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return {}
    return {name.lower(): name for name in sorted(names) if os.path.isfile(os.path.join(folder, name))}


def folders_by_lower_name(folder):
    try:
        names = os.listdir(folder)
    except OSError:
        return {}
    return {name.lower(): name for name in sorted(names) if os.path.isdir(os.path.join(folder, name))}


def locale_folders(data_dir):
    found = []
    for lower, actual in folders_by_lower_name(data_dir).items():
        if LOCALE_ARCHIVE_TEMPLATE % lower in files_by_lower_name(os.path.join(data_dir, actual)):
            found.append(actual)
    return sorted(found, key=lambda folder: (folder.lower() != PREFERRED_LOCALE, folder.lower(), folder))


def detect_locale(data_dir: str) -> Optional[str]:
    folders = locale_folders(data_dir)
    return folders[0] if folders else None


def resolve_locale_folder(data_dir, locale):
    if locale is None:
        return detect_locale(data_dir)
    return folders_by_lower_name(data_dir).get(locale.lower(), locale)


def custom_patch_order(listing, infix):
    pattern = re.compile(CUSTOM_PATCH_TEMPLATE % re.escape(infix), re.IGNORECASE)
    patches = []
    for lower, actual in listing.items():
        match = pattern.match(lower)
        character = match.group(1) if match else None
        if character is not None and character not in STOCK_PATCH_SUFFIXES:
            patches.append(((not character.isdigit(), character, actual), actual))
    return [actual for _, actual in sorted(patches)]


def relative_source(folder, name):
    return name if folder is None else folder + SOURCE_PATH_SEPARATOR + name


def default_archive_order(data_dir: str, locale: Optional[str]) -> List[Tuple[str, bool]]:
    root = files_by_lower_name(data_dir)
    local = files_by_lower_name(os.path.join(data_dir, locale)) if locale else {}
    order = []

    def take(listing, folder, names, custom):
        for name in names:
            actual = listing.get(name.lower())
            if actual is not None:
                order.append((relative_source(folder, actual), custom))

    take(root, None, STOCK_BASE_ARCHIVES, False)
    if locale:
        take(local, locale, [template % locale for template in STOCK_LOCALE_ARCHIVES], False)
    take(root, None, STOCK_PATCH_ARCHIVES, False)
    if locale:
        take(local, locale, [template % locale for template in STOCK_LOCALE_PATCH_ARCHIVES], False)
    take(root, None, custom_patch_order(root, ""), True)
    if locale:
        take(local, locale, custom_patch_order(local, CUSTOM_LOCALE_INFIX % locale.lower()), True)
    return order


def resolve_relative_path(data_dir, text):
    folder = data_dir
    parts = [part for part in ORDER_PATH_SEPARATORS.split(text.strip()) if part]
    resolved = []
    for index, part in enumerate(parts):
        listing = files_by_lower_name(folder) if index == len(parts) - 1 else folders_by_lower_name(folder)
        actual = listing.get(part.lower())
        if actual is None:
            return None
        resolved.append(actual)
        folder = os.path.join(folder, actual)
    return SOURCE_PATH_SEPARATOR.join(resolved) if resolved else None


def is_stock_archive_name(relative: str) -> bool:
    return bool(STOCK_ARCHIVE_NAME.match(relative.rsplit(SOURCE_PATH_SEPARATOR, 1)[-1]))


def read_archive_order(order_file: str, data_dir: str) -> List[Tuple[str, bool]]:
    with open(order_file, "r", encoding="utf-8-sig") as handle:
        lines = handle.read().splitlines()
    order = []
    seen = set()
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith(ORDER_FILE_COMMENT):
            continue
        relative = resolve_relative_path(data_dir, text)
        if relative is None:
            raise MpqError("%s:%d: no archive %s in %s" % (order_file, number, text, data_dir))
        if relative.lower() in seen:
            raise MpqError("%s:%d: %s is listed twice" % (order_file, number, relative))
        seen.add(relative.lower())
        order.append((relative, not is_stock_archive_name(relative)))
    return order


def archive_files(data_dir, folders):
    found = []
    for folder in [None] + folders:
        listing = files_by_lower_name(data_dir if folder is None else os.path.join(data_dir, folder))
        found.extend(relative_source(folder, actual) for lower, actual in listing.items()
                     if lower.endswith(ARCHIVE_EXTENSION))
    return found


ArchiveNote = namedtuple("ArchiveNote", ("name", "size", "text"))
VersionRead = namedtuple("VersionRead", ("source", "data", "error"))


def opened_archive(path: str) -> MpqArchive:
    archive = MpqArchive(path)
    try:
        archive.load_tables()
    except BaseException:
        archive.close()
        raise
    return archive


def archive_problem(error: Exception, path: str) -> str:
    if isinstance(error, OSError):
        return error.strerror or str(error)
    text = str(error)
    prefix = path + CONTEXT_SEPARATOR
    return text[len(prefix):] if text.startswith(prefix) else text


class ArchiveChain:
    def __init__(self, data_dir: str, locale: Optional[str] = None, order_file: Optional[str] = None):
        self.data_dir = data_dir
        self.locale = resolve_locale_folder(data_dir, locale)
        self.sources: List[ArchiveSource] = []
        self.archives: List[MpqArchive] = []
        self.ignored: List[str] = []
        self.unreadable: List[ArchiveNote] = []
        self.malformed: List[ArchiveNote] = []
        self._names = {}
        if order_file:
            order = read_archive_order(order_file, data_dir)
        else:
            order = default_archive_order(data_dir, self.locale)
        listed = {relative.lower() for relative, _ in order}
        scanned = locale_folders(data_dir)
        if self.locale and self.locale not in scanned:
            scanned.append(self.locale)
        ignored = [relative for relative in archive_files(data_dir, scanned) if relative.lower() not in listed]
        try:
            for relative, custom in order:
                self._open(relative, custom, ignored)
        except BaseException:
            self.close()
            raise
        self.ignored = sorted(ignored, key=lambda relative: (relative.lower(), relative))

    def _open(self, relative: str, custom: bool, ignored: List[str]) -> None:
        path = os.path.join(self.data_dir, *relative.split(SOURCE_PATH_SEPARATOR))
        try:
            size = os.path.getsize(path)
        except OSError as error:
            self.unreadable.append(ArchiveNote(relative, 0, archive_problem(error, path)))
            return
        if size == 0:
            ignored.append(relative)
            return
        try:
            archive = opened_archive(path)
        except (MpqError, OSError) as error:
            self.unreadable.append(ArchiveNote(relative, size, archive_problem(error, path)))
            return
        self.archives.append(archive)
        self.sources.append(ArchiveSource(relative, size, custom))
        self.malformed.extend(ArchiveNote(relative, size, warning) for warning in archive.warnings)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        for archive in self.archives:
            archive.close()

    def name(self, name: Union[str, bytes, MpqName]) -> MpqName:
        if isinstance(name, MpqName):
            return name
        key = self._names.get(name)
        if key is None:
            key = mpq_name(name)
            self._names[name] = key
        return key

    def entries(self, name: Union[str, bytes, MpqName]) -> Iterator[Tuple[ArchiveSource, MpqArchive, MpqEntry]]:
        key = self.name(name)
        for index in range(len(self.archives) - 1, -1, -1):
            found = self.archives[index].entry(key)
            if found is None or (found.size == 0 and not found.deleted):
                continue
            yield self.sources[index], self.archives[index], found
            if found.deleted:
                return

    def locate(self, name: Union[str, bytes, MpqName]) -> List[ArchiveSource]:
        return [source for source, _, found in self.entries(name) if not found.deleted]

    def read(self, name: Union[str, bytes, MpqName]) -> Optional[bytes]:
        key = self.name(name)
        for _, archive, found in self.entries(key):
            return None if found.deleted else archive.read_entry(key, found)
        return None

    def read_prefix(self, name: Union[str, bytes, MpqName], size: int) -> Optional[bytes]:
        key = self.name(name)
        for _, archive, found in self.entries(key):
            return None if found.deleted else archive.read_entry(key, found, size)
        return None

    def version_reads(self, name: Union[str, bytes, MpqName]) -> List[VersionRead]:
        key = self.name(name)
        reads = []
        for source, archive, found in self.entries(key):
            if found.deleted:
                continue
            try:
                reads.append(VersionRead(source, archive.read_entry(key, found), None))
            except MpqError as error:
                reads.append(VersionRead(source, None, error))
        return reads

    def versions(self, name: Union[str, bytes, MpqName]) -> List[Tuple[ArchiveSource, bytes]]:
        reads = self.version_reads(name)
        for read in reads:
            if read.error is not None:
                raise read.error
        return [(read.source, read.data) for read in reads]

    def archive_of(self, source: ArchiveSource) -> MpqArchive:
        return self.archives[self.sources.index(source)]
