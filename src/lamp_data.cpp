#include "lamp_data.h"

#include "log.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <limits>

namespace
{
constexpr char kFileMagic[4] = {'L', 'X', 'L', 'D'};
constexpr long kMaxFileBytes = 256L * 1024 * 1024;
constexpr uint32_t kCellKeyStride = kLampCellsPerSide;

struct FileHeader
{
    char magic[4];
    uint32_t version;
    uint32_t mapCount;
    uint32_t cellCount;
    uint32_t lampCount;
    uint32_t sourceCount;
    uint32_t reserved[2];
};

struct FileSource
{
    char path[kLampSourcePathBytes];
    uint64_t size;
};

struct FileMap
{
    uint32_t id;
    uint32_t firstCell;
    uint32_t cellCount;
    uint32_t firstLamp;
    uint32_t lampCount;
};

struct FileCell
{
    uint16_t x;
    uint16_t y;
    uint32_t firstLamp;
    uint32_t lampCount;
};

static_assert(sizeof(FileHeader) == 32, "lampdata.bin header");
static_assert(sizeof(FileSource) == 72, "lampdata.bin source record");
static_assert(sizeof(FileMap) == 20, "lampdata.bin map record");
static_assert(sizeof(FileCell) == 12, "lampdata.bin cell record");

struct LampFile
{
    std::vector<FileSource> sources;
    std::vector<FileMap> maps;
    std::vector<FileCell> cells;
    std::vector<CatalogLamp> lamps;
};

uint64_t ExpectedFileSize(const FileHeader& header)
{
    return sizeof(FileHeader) + static_cast<uint64_t>(header.sourceCount) * sizeof(FileSource) +
           static_cast<uint64_t>(header.mapCount) * sizeof(FileMap) +
           static_cast<uint64_t>(header.cellCount) * sizeof(FileCell) +
           static_cast<uint64_t>(header.lampCount) * sizeof(CatalogLamp);
}

template <typename T>
std::vector<T> ReadRecords(const unsigned char* bytes, size_t& offset, uint32_t count)
{
    std::vector<T> records(count);
    if (count)
        std::memcpy(records.data(), bytes + offset, static_cast<size_t>(count) * sizeof(T));
    offset += static_cast<size_t>(count) * sizeof(T);
    return records;
}

uint32_t CellKey(uint32_t x, uint32_t y)
{
    return x * kCellKeyStride + y;
}

bool MapsContiguous(const LampFile& file)
{
    uint64_t cells = 0;
    uint64_t lamps = 0;
    for (size_t i = 0; i < file.maps.size(); ++i)
    {
        const FileMap& map = file.maps[i];
        if ((i > 0 && map.id <= file.maps[i - 1].id) || map.firstCell != cells || map.firstLamp != lamps)
            return false;
        cells += map.cellCount;
        lamps += map.lampCount;
    }
    return cells == file.cells.size() && lamps == file.lamps.size();
}

bool CellsContiguous(const LampFile& file, const FileMap& map)
{
    uint64_t nextLamp = map.firstLamp;
    uint32_t previousKey = 0;
    for (uint32_t i = 0; i < map.cellCount; ++i)
    {
        const FileCell& cell = file.cells[map.firstCell + i];
        const uint32_t key = CellKey(cell.x, cell.y);
        if (cell.x >= kLampCellsPerSide || cell.y >= kLampCellsPerSide || (i > 0 && key <= previousKey) ||
            cell.lampCount == 0 || cell.firstLamp != nextLamp)
            return false;
        previousKey = key;
        nextLamp += cell.lampCount;
    }
    return nextLamp == static_cast<uint64_t>(map.firstLamp) + map.lampCount;
}

bool Within(float value, float lo, float hi)
{
    return std::isfinite(value) && value >= lo && value <= hi;
}

bool LampValid(const CatalogLamp& lamp, const FileCell& cell)
{
    bool valid = Within(lamp.position[0], -kMaxLampHorizontalYards, kMaxLampHorizontalYards) &&
                 Within(lamp.position[1], -kMaxLampHorizontalYards, kMaxLampHorizontalYards) &&
                 Within(lamp.position[2], -kMaxLampHeightYards, kMaxLampHeightYards) &&
                 Within(lamp.reach, 0.0f, kMaxLampReachYards) && lamp.reach > 0.0f &&
                 lamp.kind <= kLampKindChandelier && lamp.route >= kLampRouteAuthored &&
                 lamp.route <= kLampRouteEmissive;
    for (int channel = 0; channel < 3; ++channel)
        valid = valid && Within(lamp.color[channel], 0.0f, kMaxLampColor);
    return valid && LampCellOf(lamp.position[0]) == cell.x && LampCellOf(lamp.position[1]) == cell.y;
}

bool CellLampsValid(const LampFile& file, const FileCell& cell)
{
    for (uint32_t i = 0; i < cell.lampCount; ++i)
        if (!LampValid(file.lamps[cell.firstLamp + i], cell))
            return false;
    return true;
}

const char* ValidateLampFile(const LampFile& file)
{
    if (!MapsContiguous(file))
        return "maps out of order, or their cell and lamp ranges do not follow each other";
    for (const FileMap& map : file.maps)
        if (!CellsContiguous(file, map))
            return "a map's cells are out of order, empty or do not cover its lamps";
    for (const FileCell& cell : file.cells)
        if (!CellLampsValid(file, cell))
            return "a lamp is out of range or outside its cell";
    return nullptr;
}

const char* ParseLampFile(const unsigned char* bytes, size_t size, LampFile& out)
{
    if (!bytes || size < sizeof(FileHeader))
        return "shorter than its header";
    FileHeader header;
    std::memcpy(&header, bytes, sizeof(header));
    if (std::memcmp(header.magic, kFileMagic, sizeof(kFileMagic)) != 0)
        return "not a lamp data file";
    if (header.version != kLampDataVersion)
        return "another format version than this build reads; regenerate it with tools/extract_lamps.py";
    if (header.sourceCount > kMaxLampSources)
        return "more than 1024 source archives";
    if (ExpectedFileSize(header) != size)
        return "truncated or padded";
    size_t offset = sizeof(FileHeader);
    out.sources = ReadRecords<FileSource>(bytes, offset, header.sourceCount);
    out.maps = ReadRecords<FileMap>(bytes, offset, header.mapCount);
    out.cells = ReadRecords<FileCell>(bytes, offset, header.cellCount);
    out.lamps = ReadRecords<CatalogLamp>(bytes, offset, header.lampCount);
    return ValidateLampFile(out);
}

std::string SourcePath(const FileSource& source)
{
    const void* end = std::memchr(source.path, '\0', sizeof(source.path));
    const size_t length = end ? static_cast<size_t>(static_cast<const char*>(end) - source.path) : sizeof(source.path);
    return std::string(source.path, length);
}

bool ReadWholeFile(std::FILE* f, std::vector<unsigned char>& bytes)
{
    if (std::fseek(f, 0, SEEK_END) != 0)
        return false;
    const long size = std::ftell(f);
    if (size < 0 || size > kMaxFileBytes || std::fseek(f, 0, SEEK_SET) != 0)
        return false;
    bytes.resize(static_cast<size_t>(size));
    return bytes.empty() || std::fread(bytes.data(), 1, bytes.size(), f) == bytes.size();
}

double CellEdge(int index)
{
    return index * kLampCellYards - kLampGridOriginYards;
}

double DistanceOutside(double value, int index)
{
    const double lo = index == 0 ? -std::numeric_limits<double>::infinity() : CellEdge(index);
    const double hi = index == kLampCellsPerSide - 1 ? std::numeric_limits<double>::infinity() : CellEdge(index + 1);
    return value < lo ? lo - value : value > hi ? value - hi : 0.0;
}
}

int LampCellOf(double coordinate)
{
    const double cell = std::floor((coordinate + kLampGridOriginYards) / kLampCellYards);
    return static_cast<int>(std::clamp(cell, 0.0, static_cast<double>(kLampCellsPerSide - 1)));
}

void LampCatalog::Clear()
{
    m_maps.clear();
    m_cells.clear();
    m_lamps.clear();
    m_sources.clear();
    std::fill(std::begin(m_routeCounts), std::end(m_routeCounts), 0u);
    m_problem.clear();
    m_loaded = false;
}

bool LampCatalog::Parse(const unsigned char* bytes, size_t size)
{
    Clear();
    LampFile file;
    if (const char* problem = ParseLampFile(bytes, size, file))
    {
        m_problem = problem;
        return false;
    }
    for (const FileSource& source : file.sources)
        m_sources.push_back({SourcePath(source), source.size});
    for (const FileMap& map : file.maps)
        m_maps.push_back({map.id, map.firstCell, map.cellCount, map.firstLamp, map.lampCount});
    for (const FileCell& cell : file.cells)
        m_cells.push_back({cell.x, cell.y, cell.firstLamp, cell.lampCount});
    m_lamps = std::move(file.lamps);
    for (const CatalogLamp& lamp : m_lamps)
        ++m_routeCounts[lamp.route];
    m_loaded = true;
    return true;
}

bool LampCatalog::Load(const std::string& path)
{
    Clear();
    std::FILE* f = std::fopen(path.c_str(), "rb");
    if (!f)
    {
        VF_LOG_INFO("no lamp data at %s; only the client's own lights glow", path.c_str());
        return false;
    }
    std::vector<unsigned char> bytes;
    const bool read = ReadWholeFile(f, bytes);
    std::fclose(f);
    if (!read || !Parse(bytes.data(), bytes.size()))
    {
        VF_LOG_ERROR("lamp data %s is invalid (%s); only the client's own lights glow", path.c_str(),
                     read ? m_problem.c_str() : "it could not be read");
        return false;
    }
    VF_LOG_INFO("lamp data: %u lamps on %u maps in %u cells from %u archives; glowing in the fog: %u restored, %u "
                "flame, %u name, %u emissive; left to the client's own lights: %u authored",
                LampCount(), MapCount(), CellCount(), SourceCount(), RouteLampCount(kLampRouteRestored),
                RouteLampCount(kLampRouteFlame), RouteLampCount(kLampRouteName), RouteLampCount(kLampRouteEmissive),
                RouteLampCount(kLampRouteAuthored));
    for (uint32_t i = 0; i < SourceCount(); ++i)
        VF_LOG_DEBUG("  lamp data source %u: %s, %llu bytes", i, m_sources[i].path.c_str(),
                     static_cast<unsigned long long>(m_sources[i].size));
    return true;
}

uint32_t LampCatalog::MapLampCount(int mapId) const
{
    const Map* map = FindMap(mapId);
    return map ? map->lampCount : 0;
}

const LampCatalog::Map* LampCatalog::FindMap(int mapId) const
{
    if (mapId < 0)
        return nullptr;
    const uint32_t id = static_cast<uint32_t>(mapId);
    const auto found =
        std::lower_bound(m_maps.begin(), m_maps.end(), id, [](const Map& map, uint32_t key) { return map.id < key; });
    return found != m_maps.end() && found->id == id ? &*found : nullptr;
}

const LampCatalog::Cell* LampCatalog::FirstCellFrom(const Map& map, int x, int y) const
{
    const uint32_t key = CellKey(static_cast<uint32_t>(x), static_cast<uint32_t>(y));
    return std::lower_bound(m_cells.data() + map.firstCell, CellsEnd(map), key,
                            [](const Cell& cell, uint32_t wanted) { return CellKey(cell.x, cell.y) < wanted; });
}

bool LampCatalog::QueryValid(const float position[3], float radius)
{
    return std::isfinite(position[0]) && std::isfinite(position[1]) && std::isfinite(position[2]) &&
           std::isfinite(radius) && radius >= 0.0f;
}

LampCatalog::CellSpan LampCatalog::CellsAround(const float position[3], float radius)
{
    const double x = position[0];
    const double y = position[1];
    return {LampCellOf(x - radius), LampCellOf(x + radius), LampCellOf(y - radius), LampCellOf(y + radius)};
}

bool LampCatalog::CellMeetsCircle(const Cell& cell, const float position[3], float radius)
{
    const double dx = DistanceOutside(position[0], cell.x);
    const double dy = DistanceOutside(position[1], cell.y);
    return dx * dx + dy * dy <= static_cast<double>(radius) * radius;
}

double LampCatalog::SquaredDistance(const float a[3], const float b[3])
{
    double sum = 0.0;
    for (int i = 0; i < 3; ++i)
    {
        const double delta = static_cast<double>(a[i]) - b[i];
        sum += delta * delta;
    }
    return sum;
}

LampCatalog& GlobalLampCatalog()
{
    static LampCatalog catalog;
    return catalog;
}
