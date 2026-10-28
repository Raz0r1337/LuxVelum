import bz2
import hashlib
import os
import struct
import zlib
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

import lamp_mpq as mpq

MASK32 = 0xFFFFFFFF
WORD_SIZE = 4
KEY_SEED = 0xEEEEEEEE
KEY_MIX_OFFSET = 0x400
CRYPT_ROW = 0x100
HASH_ENTRY_DELETED = 0xFFFFFFFE
HASH_ENTRY_FREE = 0xFFFFFFFF
MINIMUM_HASH_TABLE_SIZE = 4
HEADER_SIZES = {1: 0x20, 2: 0x2C, 3: 0x44, 4: 0xD0}
FORMAT_VERSIONS = {1: 0, 2: 1, 3: 2, 4: 3}
HEADER_MD5_SPAN = 0xC0
MD5_SIZE = 16
USER_DATA_HEADER_SIZE = 16
HASH_POSITION_FIELD = 0x10
BLOCK_POSITION_FIELD = 0x14
HASH_COUNT_FIELD = 0x18
BLOCK_COUNT_FIELD = 0x1C
TABLE_ENTRY_SIZE = 16
PREFIX_FILLER = b"J"
LISTFILE_NAME = "(listfile)"
LISTFILE_SEPARATOR = "\r\n"
MARKER_NAME = "marker.txt"

MASK_ZLIB = 0x02
MASK_PKWARE = 0x08
MASK_BZIP2 = 0x10
COMPRESS_METHODS = {"zlib": MASK_ZLIB, "bzip2": MASK_BZIP2, "pkware": MASK_PKWARE, "zlib+bzip2": MASK_ZLIB | MASK_BZIP2}
IMPLODE_METHOD = "implode"

PKWARE_MAX_REPEAT = mpq.PKWARE_END_OF_STREAM - 1
PKWARE_DISTANCE_SYMBOLS = len(mpq.PKWARE_DISTANCE_CODES)
PKWARE_SHORT_REPEAT_REACH = PKWARE_DISTANCE_SYMBOLS << mpq.PKWARE_SHORT_REPEAT_DISTANCE_BITS
PKWARE_MATCH_CANDIDATES = 48


@dataclass
class FixtureFile:
    name: str
    data: bytes = b""
    compression: Optional[str] = None
    single_unit: bool = False
    encrypted: bool = False
    fix_key: bool = False
    sector_crc: bool = False
    locale: int = 0
    platform: int = 0
    delete_marker: bool = False
    forced_mask: Optional[int] = None
    corrupt_payload: bool = False
    implode_ascii: bool = False
    implode_dictionary_bits: int = 6
    extra_flags: int = 0


def encrypt_bytes(data: bytes, key: int) -> bytes:
    count = len(data) // WORD_SIZE
    words = list(struct.unpack_from("<%dI" % count, data))
    seed = KEY_SEED
    mix = mpq.CRYPT_TABLE[KEY_MIX_OFFSET:KEY_MIX_OFFSET + CRYPT_ROW]
    for index in range(count):
        seed = (seed + mix[key & 0xFF]) & MASK32
        plain = words[index]
        words[index] = plain ^ ((key + seed) & MASK32)
        key = (((~key << 21) + 0x11111111) & MASK32) | (key >> 11)
        seed = (plain + seed + (seed << 5) + 3) & MASK32
    return struct.pack("<%dI" % count, *words) + data[count * WORD_SIZE:]


def name_hashes(name: str) -> Tuple[int, int, int]:
    normalised = mpq.normalised_name(name)
    return tuple(mpq.hash_name(normalised, hash_type) for hash_type in (0, 1, 2))


def plain_file_key(name: str, offset: int, size: int, fix_key: bool) -> int:
    normalised = mpq.normalised_name(name)
    key = mpq.hash_name(normalised[normalised.rfind(b"\\") + 1:], 3)
    return (((key + offset) & MASK32) ^ size) if fix_key else key


class BitWriter:
    def __init__(self):
        self.output = bytearray()
        self.buffer = 0
        self.count = 0

    def write(self, value, width):
        self.buffer |= value << self.count
        self.count += width
        while self.count >= 8:
            self.output.append(self.buffer & 0xFF)
            self.buffer >>= 8
            self.count -= 8

    def finish(self):
        if self.count:
            self.output.append(self.buffer & 0xFF)
        return bytes(self.output)


def write_length(writer, length):
    value = length - mpq.PKWARE_MIN_REPEAT
    symbol = max(index for index, base in enumerate(mpq.PKWARE_LENGTH_BASES) if base <= value)
    writer.write(1, 1)
    writer.write(*mpq.PKWARE_LENGTH_CODES[symbol])
    writer.write(value - mpq.PKWARE_LENGTH_BASES[symbol], mpq.PKWARE_LENGTH_EXTRA_BITS[symbol])


def write_repeat(writer, length, distance, dictionary_bits):
    write_length(writer, length)
    low_bits = mpq.PKWARE_SHORT_REPEAT_DISTANCE_BITS if length == mpq.PKWARE_MIN_REPEAT else dictionary_bits
    value = distance - 1
    writer.write(*mpq.PKWARE_DISTANCE_CODES[value >> low_bits])
    writer.write(value & ((1 << low_bits) - 1), low_bits)


def write_literal(writer, byte, ascii):
    writer.write(0, 1)
    if ascii:
        writer.write(*mpq.PKWARE_ASCII_CODES[byte])
    else:
        writer.write(byte, 8)


def pkware_stream(tokens: Sequence[Union[int, Tuple[int, int]]], dictionary_bits: int = 6, ascii: bool = False,
                  terminated: bool = True) -> bytes:
    writer = BitWriter()
    for token in tokens:
        if isinstance(token, tuple):
            write_repeat(writer, token[0], token[1], dictionary_bits)
        else:
            write_literal(writer, token, ascii)
    if terminated:
        write_length(writer, mpq.PKWARE_END_OF_STREAM)
    return bytes([1 if ascii else 0, dictionary_bits]) + writer.finish()


def match_length(data, candidate, position):
    limit = min(PKWARE_MAX_REPEAT, len(data) - position)
    length = 0
    while length < limit and data[candidate + length] == data[position + length]:
        length += 1
    return length


def longest_match(data, position, recent, dictionary_bits):
    best = (0, 0)
    reach = PKWARE_DISTANCE_SYMBOLS << dictionary_bits
    for candidate in reversed(recent.get(data[position:position + 2], [])[-PKWARE_MATCH_CANDIDATES:]):
        distance = position - candidate
        if distance > reach:
            break
        length = match_length(data, candidate, position)
        if length == mpq.PKWARE_MIN_REPEAT and distance > PKWARE_SHORT_REPEAT_REACH:
            continue
        if length > best[0]:
            best = (length, distance)
    return best


def implode_tokens(data, dictionary_bits):
    tokens = []
    recent = {}
    position = 0
    while position < len(data):
        length, distance = longest_match(data, position, recent, dictionary_bits)
        step = length if length >= mpq.PKWARE_MIN_REPEAT else 1
        tokens.append((length, distance) if step > 1 else data[position])
        for index in range(position, position + step):
            recent.setdefault(data[index:index + 2], []).append(index)
        position += step
    return tokens


def implode(data: bytes, dictionary_bits: int = 6, ascii: bool = False) -> bytes:
    return pkware_stream(implode_tokens(data, dictionary_bits), dictionary_bits, ascii)


def compress_with_mask(chunk, mask):
    packed = chunk
    if mask & MASK_ZLIB:
        packed = zlib.compress(packed, 9)
    if mask & MASK_PKWARE:
        packed = implode(packed)
    if mask & MASK_BZIP2:
        packed = bz2.compress(packed, 9)
    return bytes([mask]) + packed


def corrupted(packed, keep):
    return packed[:keep] + bytes(byte ^ 0x5A for byte in packed[keep:])


def packed_unit(chunk, file):
    if file.forced_mask is not None:
        return bytes([file.forced_mask]) + zlib.compress(chunk, 9)
    if file.compression == IMPLODE_METHOD:
        packed = implode(chunk, file.implode_dictionary_bits, file.implode_ascii)
        keep = 2
    else:
        packed = compress_with_mask(chunk, COMPRESS_METHODS[file.compression])
        keep = 1
    if file.corrupt_payload:
        return corrupted(packed, keep)
    return packed if len(packed) < len(chunk) else chunk


def block_flags(file):
    flags = mpq.FILE_EXISTS | file.extra_flags
    if file.delete_marker:
        return flags | mpq.FILE_DELETE_MARKER
    if file.compression == IMPLODE_METHOD:
        flags |= mpq.FILE_IMPLODE
    elif file.compression is not None or file.forced_mask is not None:
        flags |= mpq.FILE_COMPRESS
    if file.encrypted:
        flags |= mpq.FILE_ENCRYPTED
    if file.fix_key:
        flags |= mpq.FILE_FIX_KEY
    if file.single_unit:
        flags |= mpq.FILE_SINGLE_UNIT
    if file.sector_crc:
        flags |= mpq.FILE_SECTOR_CRC
    return flags


def compressed(file):
    return file.compression is not None or file.forced_mask is not None


def single_unit_body(file, key):
    body = packed_unit(file.data, file) if compressed(file) else file.data
    return encrypt_bytes(body, key) if key is not None else body


def plain_sector_body(file, key, sector_size):
    sectors = [file.data[start:start + sector_size] for start in range(0, len(file.data), sector_size)]
    if key is None:
        return file.data
    return b"".join(encrypt_bytes(sector, (key + index) & MASK32) for index, sector in enumerate(sectors))


def compressed_sector_body(file, key, sector_size):
    sectors = [file.data[start:start + sector_size] for start in range(0, len(file.data), sector_size)]
    stored = [packed_unit(sector, file) for sector in sectors]
    table_words = len(sectors) + 1 + (1 if file.sector_crc else 0)
    offsets = [table_words * WORD_SIZE]
    for sector in stored:
        offsets.append(offsets[-1] + len(sector))
    checksums = b""
    if file.sector_crc:
        checksums = struct.pack("<%dI" % len(stored), *(zlib.adler32(sector) for sector in stored))
        offsets.append(offsets[-1] + len(checksums))
    table = struct.pack("<%dI" % len(offsets), *offsets)
    if key is not None:
        table = encrypt_bytes(table, (key - 1) & MASK32)
        stored = [encrypt_bytes(sector, (key + index) & MASK32) for index, sector in enumerate(stored)]
    return table + b"".join(stored) + checksums


def file_body(file, offset, sector_size):
    if file.delete_marker or not file.data:
        return b""
    key = plain_file_key(file.name, offset, len(file.data), file.fix_key) if file.encrypted else None
    if file.single_unit:
        return single_unit_body(file, key)
    if compressed(file):
        return compressed_sector_body(file, key, sector_size)
    return plain_sector_body(file, key, sector_size)


def hash_table_entries(files, size, tombstones):
    table = [(HASH_ENTRY_FREE, HASH_ENTRY_FREE, 0xFFFF, 0xFF, 0xFF, HASH_ENTRY_FREE)] * size
    placements = [(name, 0, 0, HASH_ENTRY_DELETED) for name in tombstones]
    placements += [(file.name, file.locale, file.platform, index) for index, file in enumerate(files)]
    for name, locale, platform, block in placements:
        index_hash, name_a, name_b = name_hashes(name)
        slot = index_hash & (size - 1)
        for _ in range(size):
            if table[slot][5] == HASH_ENTRY_FREE:
                break
            slot = (slot + 1) & (size - 1)
        else:
            raise ValueError("the hash table of %d entries is full" % size)
        table[slot] = (name_a, name_b, locale, platform, 0, block)
    return b"".join(struct.pack("<IIHBBI", *entry) for entry in table)


def default_hash_table_size(entry_count):
    size = MINIMUM_HASH_TABLE_SIZE
    while size < 2 * entry_count:
        size *= 2
    return size


def stored_table(table, key, compress):
    if compress:
        packed = bytes([MASK_ZLIB]) + zlib.compress(table, 9)
        if len(packed) < len(table):
            table = packed
    return encrypt_bytes(table, key)


def header_bytes(version, sector_shift, layout):
    header_size = HEADER_SIZES[version]
    archive_size = layout["archive_size"]
    header = struct.pack("<4sIIHHIIII", mpq.MPQ_MAGIC, header_size, archive_size & MASK32, FORMAT_VERSIONS[version],
                         sector_shift, layout["hash_position"] & MASK32, layout["block_position"] & MASK32,
                         layout["hash_entries"], layout["block_entries"])
    if version >= 2:
        header += struct.pack("<QHH", layout["hi_position"], layout["hash_position"] >> 32,
                              layout["block_position"] >> 32)
    if version >= 3:
        header += struct.pack("<QQQ", archive_size, 0, 0)
    if version >= 4:
        header += struct.pack("<QQQQQI", len(layout["hash_table"]), len(layout["block_table"]),
                              len(layout["hi_table"]), 0, 0, 0)
        header += hashlib.md5(layout["block_table"]).digest() + hashlib.md5(layout["hash_table"]).digest()
        header += hashlib.md5(layout["hi_table"]).digest() + bytes(2 * MD5_SIZE)
        header += hashlib.md5(header[:HEADER_MD5_SPAN]).digest()
    return header


def listfile_entry(files):
    names = sorted({file.name for file in files})
    return FixtureFile(LISTFILE_NAME, LISTFILE_SEPARATOR.join(names).encode("utf-8"), compression="zlib")


def build_mpq(files: Sequence[FixtureFile], version: int = 1, sector_shift: int = 3,
              hash_table_size: Optional[int] = None, tombstones: Sequence[str] = (), listfile: bool = False,
              hi_block: Optional[Dict[int, int]] = None, compress_tables: bool = False) -> bytes:
    files = list(files) + ([listfile_entry(files)] if listfile else [])
    sector_size = 512 << sector_shift
    position = HEADER_SIZES[version]
    bodies = []
    blocks = []
    for file in files:
        body = file_body(file, position, sector_size)
        bodies.append(body)
        blocks.append(struct.pack("<IIII", position & MASK32, len(body), len(file.data), block_flags(file)))
        position += len(body)
    size = hash_table_size or default_hash_table_size(len(files) + len(tombstones))
    hash_table = stored_table(hash_table_entries(files, size, tombstones), mpq.HASH_TABLE_KEY, compress_tables)
    block_table = stored_table(b"".join(blocks), mpq.BLOCK_TABLE_KEY, compress_tables) if blocks else b""
    hi_table = b""
    if hi_block is not None:
        hi_table = struct.pack("<%dH" % len(files), *(hi_block.get(index, 0) for index in range(len(files))))
    layout = {"hash_position": position, "hash_entries": size, "hash_table": hash_table,
              "block_position": position + len(hash_table), "block_entries": len(files), "block_table": block_table,
              "hi_position": position + len(hash_table) + len(block_table) if hi_table else 0, "hi_table": hi_table,
              "archive_size": position + len(hash_table) + len(block_table) + len(hi_table)}
    return header_bytes(version, sector_shift, layout) + b"".join(bodies) + hash_table + block_table + hi_table


def with_hash_table_last(archive: bytes) -> bytes:
    header_size = HEADER_SIZES[1]
    hash_position, block_position, hash_entries, block_entries = struct.unpack_from("<4I", archive,
                                                                                    HASH_POSITION_FIELD)
    hash_table = archive[hash_position:hash_position + hash_entries * TABLE_ENTRY_SIZE]
    block_table = archive[block_position:block_position + block_entries * TABLE_ENTRY_SIZE]
    header = bytearray(archive[:header_size])
    struct.pack_into("<2I", header, HASH_POSITION_FIELD, hash_position + len(block_table), hash_position)
    return bytes(header) + archive[header_size:hash_position] + block_table + hash_table


def with_header_words(archive: bytes, offset: int, *values: int) -> bytes:
    patched = bytearray(archive)
    struct.pack_into("<%dI" % len(values), patched, offset, *values)
    return bytes(patched)


def with_user_data(archive: bytes, header_offset: int) -> bytes:
    user_data = struct.pack("<4sIII", mpq.USER_DATA_MAGIC, header_offset, header_offset, USER_DATA_HEADER_SIZE)
    return user_data.ljust(header_offset, b"\0") + archive


def write_mpq(path: str, files: Sequence[FixtureFile], prefix_size: int = 0, user_data_offset: Optional[int] = None,
              trailing: bytes = b"", **options) -> str:
    archive = build_mpq(files, **options)
    if user_data_offset is not None:
        archive = with_user_data(archive, user_data_offset)
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(PREFIX_FILLER * prefix_size + archive + trailing)
    return path


def write_marker_archive(path: str, label: str, files: Sequence[FixtureFile] = (), **options) -> str:
    return write_mpq(path, [FixtureFile(MARKER_NAME, label.encode("utf-8"), compression="zlib")] + list(files),
                     **options)
