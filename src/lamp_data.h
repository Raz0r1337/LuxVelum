#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

constexpr uint8_t kLampRouteAuthored = 1;
constexpr uint8_t kLampRouteRestored = 2;
constexpr uint8_t kLampRouteFlame = 3;
constexpr uint8_t kLampRouteName = 4;
constexpr uint8_t kLampRouteEmissive = 5;
constexpr uint8_t kLampRouteCount = 6;
constexpr uint8_t kLampKindUnknown = 0;
constexpr uint8_t kLampKindCandle = 1;
constexpr uint8_t kLampKindTorch = 2;
constexpr uint8_t kLampKindBrazier = 3;
constexpr uint8_t kLampKindBonfire = 4;
constexpr uint8_t kLampKindLamp = 5;
constexpr uint8_t kLampKindChandelier = 6;
constexpr uint16_t kLampFlagWmoDoodad = 0x1;
constexpr uint16_t kLampFlagBoundsFallback = 0x2;
constexpr uint16_t kLampFlagClampedToModel = 0x4;
constexpr uint16_t kLampFlagGlobalWmo = 0x8;
constexpr uint16_t kLampFlagDeadAuthoredBlocks = 0x10;

constexpr uint32_t kLampDataVersion = 1;
constexpr uint32_t kMaxLampSources = 1024;
constexpr size_t kLampSourcePathBytes = 64;
constexpr int kLampCellsPerSide = 256;
constexpr double kLampGridOriginYards = 17066.666;
constexpr double kLampCellYards = 133.33333;
constexpr float kMaxLampHorizontalYards = 17068.0f;
constexpr float kMaxLampHeightYards = 20000.0f;
constexpr float kMaxLampReachYards = 200.0f;
constexpr float kMaxLampColor = 64.0f;

struct CatalogLamp
{
    float position[3];
    float color[3];
    float reach;
    uint16_t flags;
    uint8_t kind;
    uint8_t route;
};

static_assert(sizeof(CatalogLamp) == 32, "a lampdata.bin lamp record is 32 bytes");

struct LampSourceArchive
{
    std::string path;
    uint64_t size;
};

int LampCellOf(double coordinate);

class LampCatalog
{
public:
    bool Load(const std::string& path);
    bool Parse(const unsigned char* bytes, size_t size);
    void Clear();
    bool Loaded() const { return m_loaded; }
    const std::string& Problem() const { return m_problem; }
    uint32_t MapCount() const { return static_cast<uint32_t>(m_maps.size()); }
    uint32_t CellCount() const { return static_cast<uint32_t>(m_cells.size()); }
    uint32_t LampCount() const { return static_cast<uint32_t>(m_lamps.size()); }
    uint32_t SourceCount() const { return static_cast<uint32_t>(m_sources.size()); }
    const LampSourceArchive& Source(uint32_t index) const { return m_sources[index]; }
    uint32_t RouteLampCount(uint8_t route) const { return route < kLampRouteCount ? m_routeCounts[route] : 0; }
    uint32_t MapLampCount(int mapId) const;

    template <typename Visit>
    void VisitLampsWithin(int mapId, const float position[3], float radius, Visit visit) const;

private:
    struct Map
    {
        uint32_t id;
        uint32_t firstCell;
        uint32_t cellCount;
        uint32_t firstLamp;
        uint32_t lampCount;
    };

    struct Cell
    {
        uint16_t x;
        uint16_t y;
        uint32_t firstLamp;
        uint32_t lampCount;
    };

    struct CellSpan
    {
        int firstX;
        int lastX;
        int firstY;
        int lastY;
    };

    const Map* FindMap(int mapId) const;
    const Cell* FirstCellFrom(const Map& map, int x, int y) const;
    const Cell* CellsEnd(const Map& map) const { return m_cells.data() + map.firstCell + map.cellCount; }
    static bool QueryValid(const float position[3], float radius);
    static CellSpan CellsAround(const float position[3], float radius);
    static bool CellInRow(const Cell& cell, int x, int lastY) { return cell.x == x && cell.y <= lastY; }
    static bool CellMeetsCircle(const Cell& cell, const float position[3], float radius);
    static double SquaredDistance(const float a[3], const float b[3]);
    template <typename Visit>
    void VisitCellLamps(const Map& map, const Cell& cell, const float position[3], double radiusSquared,
                        Visit& visit) const;

    std::vector<Map> m_maps;
    std::vector<Cell> m_cells;
    std::vector<CatalogLamp> m_lamps;
    std::vector<LampSourceArchive> m_sources;
    uint32_t m_routeCounts[kLampRouteCount] = {};
    std::string m_problem;
    bool m_loaded = false;
};

template <typename Visit>
void LampCatalog::VisitCellLamps(const Map& map, const Cell& cell, const float position[3], double radiusSquared,
                                 Visit& visit) const
{
    for (uint32_t index = cell.firstLamp; index < cell.firstLamp + cell.lampCount; ++index)
        if (SquaredDistance(m_lamps[index].position, position) <= radiusSquared)
            visit(m_lamps[index], index - map.firstLamp);
}

template <typename Visit>
void LampCatalog::VisitLampsWithin(int mapId, const float position[3], float radius, Visit visit) const
{
    const Map* map = FindMap(mapId);
    if (!map || !QueryValid(position, radius))
        return;
    const double radiusSquared = static_cast<double>(radius) * radius;
    const CellSpan span = CellsAround(position, radius);
    const Cell* end = CellsEnd(*map);
    for (int x = span.firstX; x <= span.lastX; ++x)
        for (const Cell* cell = FirstCellFrom(*map, x, span.firstY); cell != end && CellInRow(*cell, x, span.lastY);
             ++cell)
            if (CellMeetsCircle(*cell, position, radius))
                VisitCellLamps(*map, *cell, position, radiusSquared, visit);
}

LampCatalog& GlobalLampCatalog();
