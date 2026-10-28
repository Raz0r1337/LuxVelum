#pragma once

namespace lamp_data_checks
{
constexpr int kFixtureMap = 0;
constexpr int kOtherFixtureMap = 530;
constexpr int kGridMap = 1;
constexpr size_t kHeaderBytes = 32;
constexpr size_t kSourceBytes = 72;
constexpr size_t kMapBytes = 20;
constexpr size_t kCellBytes = 12;
constexpr size_t kLampBytes = 32;
constexpr size_t kHeaderVersion = 4;
constexpr size_t kHeaderMapCount = 8;
constexpr size_t kHeaderCellCount = 12;
constexpr size_t kHeaderLampCount = 16;
constexpr size_t kHeaderSourceCount = 20;
constexpr size_t kMapFirstLamp = 12;
constexpr size_t kCellX = 0;
constexpr size_t kCellLampCount = 8;
constexpr size_t kLampX = 0;
constexpr size_t kLampZ = 8;
constexpr size_t kLampRed = 12;
constexpr size_t kLampReach = 24;
constexpr size_t kLampKind = 30;
constexpr size_t kLampRoute = 31;
constexpr uint32_t kCellKeyStride = 256;
constexpr float kLampFrameSeconds = 1.0f / 60.0f;
constexpr int kLampFadeFrames = static_cast<int>(kLocalLightFadeSeconds / kLampFrameSeconds + 0.5f);
constexpr uintptr_t kFirstNativeAddress = 0x00200000;
constexpr uintptr_t kNativeStride = 0x6C + 4;

struct MapLamps
{
    uint32_t mapId;
    std::vector<CatalogLamp> lamps;
};

CatalogLamp FixtureLamp(float x, float y, float z, uint8_t route, uint8_t kind = kLampKindTorch, float peak = 1.0f)
{
    CatalogLamp lamp = {};
    lamp.position[0] = x;
    lamp.position[1] = y;
    lamp.position[2] = z;
    lamp.color[0] = peak;
    lamp.color[1] = peak * 0.6f;
    lamp.color[2] = peak * 0.3f;
    lamp.reach = 12.0f;
    lamp.kind = kind;
    lamp.route = route;
    return lamp;
}

template <typename T>
void Append(std::vector<unsigned char>& bytes, const T& value)
{
    const auto* raw = reinterpret_cast<const unsigned char*>(&value);
    bytes.insert(bytes.end(), raw, raw + sizeof(T));
}

template <typename T>
void Put(std::vector<unsigned char>& bytes, size_t offset, const T& value)
{
    std::memcpy(bytes.data() + offset, &value, sizeof(T));
}

template <typename T>
T Get(const std::vector<unsigned char>& bytes, size_t offset)
{
    T value;
    std::memcpy(&value, bytes.data() + offset, sizeof(T));
    return value;
}

uint32_t CellKeyOf(const CatalogLamp& lamp)
{
    return static_cast<uint32_t>(LampCellOf(lamp.position[0])) * kCellKeyStride +
           static_cast<uint32_t>(LampCellOf(lamp.position[1]));
}

void AppendSource(std::vector<unsigned char>& bytes, const std::string& name, uint64_t size)
{
    char path[kLampSourcePathBytes] = {};
    std::memcpy(path, name.data(), std::min(name.size(), sizeof(path) - 1));
    bytes.insert(bytes.end(), path, path + sizeof(path));
    Append(bytes, size);
}

std::vector<unsigned char> LampFileBytes(std::vector<MapLamps> maps, const std::vector<std::string>& sources,
                                         const std::vector<uint64_t>& sourceSizes = {})
{
    std::sort(maps.begin(), maps.end(), [](const MapLamps& a, const MapLamps& b) { return a.mapId < b.mapId; });
    std::vector<unsigned char> mapBytes;
    std::vector<unsigned char> cellBytes;
    std::vector<unsigned char> lampBytes;
    uint32_t cellCount = 0;
    uint32_t lampCount = 0;
    for (MapLamps& map : maps)
    {
        std::stable_sort(map.lamps.begin(), map.lamps.end(),
                         [](const CatalogLamp& a, const CatalogLamp& b) { return CellKeyOf(a) < CellKeyOf(b); });
        const uint32_t firstCell = cellCount;
        for (size_t first = 0; first < map.lamps.size();)
        {
            const uint32_t key = CellKeyOf(map.lamps[first]);
            size_t end = first;
            while (end < map.lamps.size() && CellKeyOf(map.lamps[end]) == key)
                ++end;
            Append(cellBytes, static_cast<uint16_t>(key / kCellKeyStride));
            Append(cellBytes, static_cast<uint16_t>(key % kCellKeyStride));
            Append(cellBytes, static_cast<uint32_t>(lampCount + first));
            Append(cellBytes, static_cast<uint32_t>(end - first));
            ++cellCount;
            first = end;
        }
        for (const CatalogLamp& lamp : map.lamps)
            Append(lampBytes, lamp);
        for (uint32_t field : {map.mapId, firstCell, cellCount - firstCell, lampCount,
                               static_cast<uint32_t>(map.lamps.size())})
            Append(mapBytes, field);
        lampCount += static_cast<uint32_t>(map.lamps.size());
    }
    std::vector<unsigned char> bytes = {'L', 'X', 'L', 'D'};
    for (uint32_t field : {kLampDataVersion, static_cast<uint32_t>(maps.size()), cellCount, lampCount,
                           static_cast<uint32_t>(sources.size()), 0u, 0u})
        Append(bytes, field);
    for (size_t i = 0; i < sources.size(); ++i)
        AppendSource(bytes, sources[i], i < sourceSizes.size() ? sourceSizes[i] : 1000 + i);
    bytes.insert(bytes.end(), mapBytes.begin(), mapBytes.end());
    bytes.insert(bytes.end(), cellBytes.begin(), cellBytes.end());
    bytes.insert(bytes.end(), lampBytes.begin(), lampBytes.end());
    return bytes;
}

std::vector<MapLamps> FixtureMaps()
{
    return {{kOtherFixtureMap,
             {FixtureLamp(-1000.0f, 1000.0f, 120.0f, kLampRouteFlame, kLampKindBrazier),
              FixtureLamp(-1000.5f, 1100.0f, 120.0f, kLampRouteRestored, kLampKindLamp)}},
            {kFixtureMap,
             {FixtureLamp(100.0f, 200.0f, 50.0f, kLampRouteFlame),
              FixtureLamp(101.5f, 200.0f, 50.0f, kLampRouteAuthored, kLampKindLamp),
              FixtureLamp(300.0f, -250.0f, 10.0f, kLampRouteName, kLampKindLamp),
              FixtureLamp(-5000.0f, 4000.0f, 80.0f, kLampRouteEmissive, kLampKindChandelier),
              FixtureLamp(17060.0f, -17060.0f, 0.0f, kLampRouteRestored, kLampKindCandle)}}};
}

const std::vector<std::string> kFixtureSources = {"patch-4.MPQ", "enUS\\patch-enUS-5.MPQ"};

std::vector<unsigned char> FixtureFile()
{
    return LampFileBytes(FixtureMaps(), kFixtureSources);
}

bool Parses(LampCatalog& catalog, const std::vector<unsigned char>& bytes)
{
    return catalog.Parse(bytes.data(), bytes.size());
}

struct FileLayout
{
    size_t maps;
    size_t cells;
    size_t lamps;
};

FileLayout LayoutOf(const std::vector<unsigned char>& bytes)
{
    const size_t maps = kHeaderBytes + Get<uint32_t>(bytes, kHeaderSourceCount) * kSourceBytes;
    const size_t cells = maps + Get<uint32_t>(bytes, kHeaderMapCount) * kMapBytes;
    const size_t lamps = cells + Get<uint32_t>(bytes, kHeaderCellCount) * kCellBytes;
    return {maps, cells, lamps};
}

struct VisitedLamp
{
    uint32_t index;
    CatalogLamp lamp;
};

std::vector<VisitedLamp> LampsWithin(const LampCatalog& catalog, int mapId, float x, float y, float z, float radius)
{
    const float position[3] = {x, y, z};
    std::vector<VisitedLamp> visited;
    catalog.VisitLampsWithin(mapId, position, radius,
                             [&](const CatalogLamp& lamp, uint32_t index) { visited.push_back({index, lamp}); });
    std::sort(visited.begin(), visited.end(),
              [](const VisitedLamp& a, const VisitedLamp& b) { return a.index < b.index; });
    return visited;
}

bool SamePosition(const CatalogLamp& lamp, float x, float y, float z)
{
    return lamp.position[0] == x && lamp.position[1] == y && lamp.position[2] == z;
}

uint32_t IndexAt(const LampCatalog& catalog, int mapId, float x, float y, float z)
{
    for (const VisitedLamp& visited : LampsWithin(catalog, mapId, x, y, z, 0.0f))
        if (SamePosition(visited.lamp, x, y, z))
            return visited.index;
    return UINT32_MAX;
}

void CheckParserAcceptsTheFixture()
{
    LampCatalog catalog;
    const std::vector<unsigned char> bytes = FixtureFile();
    const bool parsed = Parses(catalog, bytes);
    const std::vector<VisitedLamp> pair = LampsWithin(catalog, kFixtureMap, 100.0f, 200.0f, 50.0f, 2.0f);
    std::printf("     lamp fixture: %zu bytes, %u maps, %u cells, %u lamps, %u sources\n", bytes.size(),
                catalog.MapCount(), catalog.CellCount(), catalog.LampCount(), catalog.SourceCount());
    Check(parsed && catalog.Loaded() && catalog.Problem().empty() && catalog.MapCount() == 2 &&
              catalog.CellCount() == 6 && catalog.LampCount() == 7 && catalog.MapLampCount(kFixtureMap) == 5 &&
              catalog.MapLampCount(kOtherFixtureMap) == 2 && catalog.MapLampCount(kGridMap) == 0 &&
              catalog.MapLampCount(-1) == 0 && catalog.RouteLampCount(kLampRouteAuthored) == 1 &&
              catalog.RouteLampCount(kLampRouteRestored) == 2 && catalog.RouteLampCount(kLampRouteFlame) == 2 &&
              catalog.RouteLampCount(kLampRouteName) == 1 && catalog.RouteLampCount(kLampRouteEmissive) == 1,
          "lampdata.bin parses with its maps, cells, lamps and per-route counts");
    Check(catalog.SourceCount() == 2 && catalog.Source(0).path == "patch-4.MPQ" &&
              catalog.Source(1).path == "enUS\\patch-enUS-5.MPQ" && catalog.Source(1).size == 1001 &&
              pair.size() == 2 && pair[0].index < catalog.MapLampCount(kFixtureMap) &&
              pair[1].index < catalog.MapLampCount(kFixtureMap) && pair[0].index != pair[1].index &&
              (pair[0].lamp.route == kLampRouteAuthored) != (pair[1].lamp.route == kLampRouteAuthored) &&
              IndexAt(catalog, kFixtureMap, 17060.0f, -17060.0f, 0.0f) != UINT32_MAX &&
              IndexAt(catalog, kOtherFixtureMap, -1000.5f, 1100.0f, 120.0f) != UINT32_MAX,
          "lampdata.bin keeps its source archives, and a lamp is found by map with its index within that map");

    LampCatalog empty;
    std::vector<unsigned char> headerOnly = LampFileBytes({}, {});
    Check(Parses(empty, headerOnly) && empty.Loaded() && empty.LampCount() == 0 && empty.MapCount() == 0,
          "a lampdata.bin without lamps is valid and empty");
}

using Breakage = void (*)(std::vector<unsigned char>&);

struct BrokenVariant
{
    const char* name;
    Breakage breakage;
};

void PutLampFloat(std::vector<unsigned char>& bytes, size_t lamp, size_t field, float value)
{
    Put(bytes, LayoutOf(bytes).lamps + lamp * kLampBytes + field, value);
}

void PutLampByte(std::vector<unsigned char>& bytes, size_t lamp, size_t field, uint8_t value)
{
    Put(bytes, LayoutOf(bytes).lamps + lamp * kLampBytes + field, value);
}

const BrokenVariant kBrokenVariants[] = {
    {"shorter than its header", [](std::vector<unsigned char>& b) { b.resize(kHeaderBytes - 1); }},
    {"another magic", [](std::vector<unsigned char>& b) { b[3] = '2'; }},
    {"version 2", [](std::vector<unsigned char>& b) { Put<uint32_t>(b, kHeaderVersion, 2); }},
    {"truncated", [](std::vector<unsigned char>& b) { b.pop_back(); }},
    {"padded", [](std::vector<unsigned char>& b) { b.push_back(0); }},
    {"maps out of order",
     [](std::vector<unsigned char>& b) {
         const size_t maps = LayoutOf(b).maps;
         const uint32_t first = Get<uint32_t>(b, maps);
         Put(b, maps, Get<uint32_t>(b, maps + kMapBytes));
         Put(b, maps + kMapBytes, first);
     }},
    {"a map's lamps not following the previous map's",
     [](std::vector<unsigned char>& b) {
         const size_t second = LayoutOf(b).maps + kMapBytes + kMapFirstLamp;
         Put(b, second, Get<uint32_t>(b, second) + 1);
     }},
    {"a lamp no map covers",
     [](std::vector<unsigned char>& b) {
         Put(b, kHeaderLampCount, Get<uint32_t>(b, kHeaderLampCount) + 1);
         b.insert(b.end(), kLampBytes, 0);
     }},
    {"an empty cell", [](std::vector<unsigned char>& b) { Put<uint32_t>(b, LayoutOf(b).cells + kCellLampCount, 0); }},
    {"cells out of order",
     [](std::vector<unsigned char>& b) {
         const size_t cells = LayoutOf(b).cells;
         const uint32_t first = Get<uint32_t>(b, cells + kCellX);
         Put(b, cells + kCellX, Get<uint32_t>(b, cells + kCellBytes + kCellX));
         Put(b, cells + kCellBytes + kCellX, first);
     }},
    {"a cell beyond the grid", [](std::vector<unsigned char>& b) { Put<uint16_t>(b, LayoutOf(b).cells, 300); }},
    {"a lamp outside its cell", [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampX, 99.0f); }},
    {"a lamp beyond the world's edge", [](std::vector<unsigned char>& b) { PutLampFloat(b, 4, kLampX, 17069.0f); }},
    {"a lamp too high", [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampZ, 20001.0f); }},
    {"a lamp at no position",
     [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampZ, std::numeric_limits<float>::quiet_NaN()); }},
    {"a lamp without reach", [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampReach, 0.0f); }},
    {"a lamp reaching too far", [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampReach, 200.5f); }},
    {"a negative colour", [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampRed, -0.1f); }},
    {"a colour above 64", [](std::vector<unsigned char>& b) { PutLampFloat(b, 0, kLampRed, 64.5f); }},
    {"an unknown kind", [](std::vector<unsigned char>& b) { PutLampByte(b, 0, kLampKind, 7); }},
    {"route 0", [](std::vector<unsigned char>& b) { PutLampByte(b, 0, kLampRoute, 0); }},
    {"route 6", [](std::vector<unsigned char>& b) { PutLampByte(b, 0, kLampRoute, 6); }},
};

void CheckParserRejectsBrokenFiles()
{
    const std::vector<unsigned char> good = FixtureFile();
    bool rejected = true;
    for (const BrokenVariant& variant : kBrokenVariants)
    {
        LampCatalog catalog;
        const bool before = Parses(catalog, good);
        std::vector<unsigned char> bytes = good;
        variant.breakage(bytes);
        const bool parsed = Parses(catalog, bytes);
        const bool cleared = !catalog.Loaded() && catalog.LampCount() == 0 && catalog.MapCount() == 0 &&
                             catalog.MapLampCount(kFixtureMap) == 0 && !catalog.Problem().empty();
        if (!before || parsed || !cleared)
            std::printf("     lamp data variant \"%s\" was %s\n", variant.name, parsed ? "accepted" : "not cleared");
        else
            std::printf("     lamp data variant \"%s\" rejected: %s\n", variant.name, catalog.Problem().c_str());
        rejected = rejected && before && !parsed && cleared;
    }
    LampCatalog catalog;
    const bool nothing = !catalog.Parse(nullptr, 0) && !catalog.Loaded();
    Check(rejected && nothing,
          "lampdata.bin is rejected whole, leaving no lamps, when its size, version, map or cell order, ranges or "
          "any lamp's position, cell, reach, colour, kind or route is wrong");

    std::vector<std::string> manySources(kMaxLampSources, "patch-x.MPQ");
    LampCatalog most;
    const bool mostParsed = Parses(most, LampFileBytes(FixtureMaps(), manySources));
    manySources.push_back("patch-y.MPQ");
    LampCatalog tooMany;
    const bool tooManyParsed = Parses(tooMany, LampFileBytes(FixtureMaps(), manySources));
    Check(mostParsed && most.SourceCount() == kMaxLampSources && !tooManyParsed && tooMany.LampCount() == 0,
          "lampdata.bin may name up to 1024 source archives and is rejected with more");
}

std::vector<CatalogLamp> GridLamps()
{
    std::vector<CatalogLamp> lamps;
    for (int i = 0; i < 30; ++i)
        for (int j = 0; j < 30; ++j)
        {
            const uint8_t route = static_cast<uint8_t>(kLampRouteAuthored + (i + j) % 5);
            lamps.push_back(FixtureLamp(-700.0f + 47.3f * static_cast<float>(i), 300.0f + 45.1f * static_cast<float>(j),
                                        static_cast<float>((i * j) % 40) - 20.0f, route));
        }
    return lamps;
}

struct RadiusQuery
{
    float x;
    float y;
    float z;
    float radius;
};

const RadiusQuery kRadiusQueries[] = {
    {0.0f, 900.0f, 0.0f, 250.0f},        {-650.0f, 320.0f, 5.0f, 60.0f},  {-533.333f, 400.0f, 0.0f, 30.0f},
    {-700.0f, 300.0f, -20.0f, 0.0f},     {-200.0f, 1000.0f, 400.0f, 410.0f}, {0.0f, 900.0f, 0.0f, 1000.0f},
    {-17060.0f, 300.0f, 0.0f, 16400.0f}, {500.0f, 2000.0f, 0.0f, 20.0f},
};

void CheckRadiusQueryAcrossCells()
{
    LampCatalog catalog;
    const bool parsed = Parses(catalog, LampFileBytes({{static_cast<uint32_t>(kGridMap), GridLamps()}}, {}));
    const std::vector<VisitedLamp> all = LampsWithin(catalog, kGridMap, 0.0f, 0.0f, 0.0f, 1.0e6f);
    bool indexed = parsed && all.size() == catalog.MapLampCount(kGridMap) && catalog.CellCount() > 50;
    for (size_t i = 0; i < all.size(); ++i)
        indexed = indexed && all[i].index == i;
    bool exact = true;
    size_t largest = 0;
    for (const RadiusQuery& query : kRadiusQueries)
    {
        const float position[3] = {query.x, query.y, query.z};
        std::vector<uint32_t> expected;
        for (const VisitedLamp& lamp : all)
        {
            double squared = 0.0;
            for (int axis = 0; axis < 3; ++axis)
            {
                const double delta = static_cast<double>(lamp.lamp.position[axis]) - position[axis];
                squared += delta * delta;
            }
            if (squared <= static_cast<double>(query.radius) * query.radius)
                expected.push_back(lamp.index);
        }
        const std::vector<VisitedLamp> visited =
            LampsWithin(catalog, kGridMap, query.x, query.y, query.z, query.radius);
        bool same = visited.size() == expected.size();
        for (size_t i = 0; same && i < visited.size(); ++i)
            same = visited[i].index == expected[i] &&
                   std::memcmp(&visited[i].lamp, &all[expected[i]].lamp, sizeof(CatalogLamp)) == 0;
        exact = exact && same;
        largest = std::max(largest, expected.size());
    }
    const bool zeroRadiusHit = LampsWithin(catalog, kGridMap, -700.0f, 300.0f, -20.0f, 0.0f).size() == 1;
    const bool invalid = LampsWithin(catalog, kGridMap, 0.0f, 900.0f, 0.0f, -1.0f).empty() &&
                         LampsWithin(catalog, kGridMap, std::numeric_limits<float>::quiet_NaN(), 900.0f, 0.0f,
                                     250.0f)
                             .empty() &&
                         LampsWithin(catalog, kGridMap, 0.0f, 900.0f, 0.0f, std::numeric_limits<float>::infinity())
                             .empty() &&
                         LampsWithin(catalog, kFixtureMap, 0.0f, 900.0f, 0.0f, 1000.0f).empty();
    std::printf("     lamp grid: %zu lamps in %u cells, largest query %zu lamps\n", all.size(), catalog.CellCount(),
                largest);
    Check(indexed && exact && zeroRadiusHit && invalid && largest == all.size(),
          "the radius query visits exactly the lamps within the distance across every cell the circle meets, with "
          "their index within the map, and nothing for another map, a negative or nonfinite radius or position");

    LampCatalog edges;
    const bool edgesParsed =
        Parses(edges, LampFileBytes({{static_cast<uint32_t>(kGridMap),
                                      {FixtureLamp(-17068.0f, -17068.0f, 0.0f, kLampRouteFlame),
                                       FixtureLamp(17068.0f, 17068.0f, 0.0f, kLampRouteFlame)}}},
                                    {}));
    Check(edgesParsed && LampsWithin(edges, kGridMap, -17060.0f, -17060.0f, 0.0f, 12.0f).size() == 1 &&
              LampsWithin(edges, kGridMap, 17060.0f, 17060.0f, 0.0f, 12.0f).size() == 1 &&
              LampCellOf(-17068.0) == 0 && LampCellOf(17068.0) == kLampCellsPerSide - 1,
          "lamps at the world's edge sit in the outermost cells and the radius query finds them there");
}

LocalLightCamera LampCamera()
{
    return ForwardViewCamera(1.0f, 1000.0f);
}

constexpr PointLightUpload kPlainUpload = {false, 1.0f, 1.0f};

LocalPointLight NativeLight(uint32_t slot, float x, float y, float z, float peak = 1.0f)
{
    LocalPointLight light;
    light.position[0] = x;
    light.position[1] = y;
    light.position[2] = z;
    light.color[0] = peak;
    light.color[1] = peak * 0.5f;
    light.color[2] = peak * 0.25f;
    light.attenuation[0] = kClientPointLightConstantAttenuation;
    light.attenuation[1] = kClientPointLightLinearAttenuation;
    light.attenuation[2] = kClientPointLightQuadraticAttenuation;
    light.nativeId = kFirstNativeAddress + slot * kNativeStride;
    return light;
}

LocalLightInputs WalkedNatives(const std::vector<LocalPointLight>& natives, const LocalLightCamera& camera,
                               const PointLightUpload& upload = kPlainUpload)
{
    LocalLightInputs inputs;
    for (const LocalPointLight& native : natives)
        engine::SelectLocalPointLightInView(inputs, native, camera, upload);
    return inputs;
}

const LocalPointLight* Candidate(const LocalLightInputs& inputs, uintptr_t id)
{
    for (uint32_t i = 0; i < inputs.candidateCount; ++i)
        if (inputs.candidates[i].nativeId == id)
            return &inputs.candidates[i];
    return nullptr;
}

struct FeedCatalog
{
    LampCatalog catalog;
    uint32_t flame;
    uint32_t authored;
    uint32_t named;
    uint32_t distant;
    uint32_t besideNative;
    uint32_t behind;
    uint32_t otherMap;
};

constexpr float kBesideNativeLamp[3] = {2.0f, 1.0f, 60.0f};
constexpr float kNativeBesideLamp[3] = {2.5f, 1.0f, 61.0f};

void BuildFeedCatalog(FeedCatalog& feed)
{
    const std::vector<MapLamps> maps = {
        {static_cast<uint32_t>(kFixtureMap),
         {FixtureLamp(0.0f, 0.0f, 30.0f, kLampRouteFlame), FixtureLamp(5.0f, 0.0f, 30.0f, kLampRouteAuthored),
          FixtureLamp(-5.0f, 0.0f, 40.0f, kLampRouteName, kLampKindLamp, 0.8f),
          FixtureLamp(0.0f, 0.0f, 300.0f, kLampRouteEmissive),
          FixtureLamp(kBesideNativeLamp[0], kBesideNativeLamp[1], kBesideNativeLamp[2], kLampRouteRestored),
          FixtureLamp(0.0f, 0.0f, -200.0f, kLampRouteFlame)}},
        {static_cast<uint32_t>(kGridMap), {FixtureLamp(0.0f, 0.0f, 30.0f, kLampRouteFlame)}}};
    Parses(feed.catalog, LampFileBytes(maps, {}));
    feed.flame = IndexAt(feed.catalog, kFixtureMap, 0.0f, 0.0f, 30.0f);
    feed.authored = IndexAt(feed.catalog, kFixtureMap, 5.0f, 0.0f, 30.0f);
    feed.named = IndexAt(feed.catalog, kFixtureMap, -5.0f, 0.0f, 40.0f);
    feed.distant = IndexAt(feed.catalog, kFixtureMap, 0.0f, 0.0f, 300.0f);
    feed.besideNative = IndexAt(feed.catalog, kFixtureMap, kBesideNativeLamp[0], kBesideNativeLamp[1],
                                kBesideNativeLamp[2]);
    feed.behind = IndexAt(feed.catalog, kFixtureMap, 0.0f, 0.0f, -200.0f);
    feed.otherMap = IndexAt(feed.catalog, kGridMap, 0.0f, 0.0f, 30.0f);
}

LampFeedSettings FeedSettings(bool enabled = true, float intensity = 1.0f, float distance = 250.0f)
{
    LampFeedSettings settings;
    settings.enabled = enabled;
    settings.intensity = intensity;
    settings.distance = distance;
    return settings;
}

LocalLightInputs Offered(LampFeed& feed, const FeedCatalog& lamps, int mapId, const LampFeedSettings& settings,
                         const std::vector<LocalPointLight>& natives = {},
                         const PointLightUpload& upload = kPlainUpload)
{
    const LocalLightCamera camera = LampCamera();
    LocalLightInputs inputs = WalkedNatives(natives, camera, upload);
    feed.Offer(lamps.catalog, mapId, camera, upload, settings, inputs);
    return inputs;
}

bool HasLamp(const LocalLightInputs& inputs, uint32_t index)
{
    return Candidate(inputs, CatalogLampIdOf(index)) != nullptr;
}

void CheckCatalogLampIds()
{
    bool odd = true;
    for (uint32_t index : {0u, 1u, 2u, 4095u, 0x3FFFFFFFu})
        odd = odd && CatalogLampId(CatalogLampIdOf(index)) && (CatalogLampIdOf(index) >> 1) == index;
    bool aligned = true;
    for (uintptr_t address : {uintptr_t{0x10000}, uintptr_t{0x00CD754C}, uintptr_t{0x7FFE0004}, uintptr_t{0}})
        aligned = aligned && !CatalogLampId(address);
    Check(odd && aligned,
          "lamps from lampdata.bin carry odd light ids built from their index within the map, which no 4-byte "
          "aligned native light address can take");
}

void CheckFeedOffersLampsWithoutAuthoredLights()
{
    FeedCatalog lamps;
    BuildFeedCatalog(lamps);
    LampFeed feed;
    const LocalLightInputs inputs = Offered(feed, lamps, kFixtureMap, FeedSettings());
    const LocalPointLight* flame = Candidate(inputs, CatalogLampIdOf(lamps.flame));
    const LampFeedCounts& counts = feed.Counts();
    std::printf("     lamp feed: %u lamps on the map, %u not authored within 250 yd, %u offered, %u pooled\n",
                counts.mapLamps, counts.nearby, counts.offered, counts.pooled);
    Check(flame && HasLamp(inputs, lamps.named) && HasLamp(inputs, lamps.besideNative) &&
              !HasLamp(inputs, lamps.authored) && !HasLamp(inputs, lamps.distant) && !HasLamp(inputs, lamps.behind) &&
              inputs.candidateCount == 3 && CatalogLampsAmong(inputs.candidates, inputs.candidateCount) == 3 &&
              counts.mapLamps == 6 && counts.nearby == 4 && counts.offered == 4 && counts.heldBack == 0 &&
              counts.pooled == 3,
          "the feed offers every lamp within LampDistance that is not an authored light of the client, under an "
          "odd id, and the view keeps one behind the camera out of the pool");
    Check(flame && flame->position[2] == 30.0f && LocalNear(flame->color[0], 1.0f) &&
              LocalNear(flame->color[1], 0.6f) && flame->attenuation[0] == kClientPointLightConstantAttenuation &&
              flame->attenuation[1] == kClientPointLightLinearAttenuation &&
              flame->attenuation[2] == kClientPointLightQuadraticAttenuation && flame->enabled == 1 &&
              LocalNear(flame->uploadedColor[0], 1.0f) && flame->cutoff > 0.0f,
          "an offered lamp shines with its colour at the client's fixed point-light falloff 0, 0.7, 0.03");
}

void CheckFeedHoldsBackLampsBesideNativeLights()
{
    FeedCatalog lamps;
    BuildFeedCatalog(lamps);
    LampFeed feed;
    const LocalPointLight native = NativeLight(0, kNativeBesideLamp[0], kNativeBesideLamp[1], kNativeBesideLamp[2]);
    const LocalLightInputs beside = Offered(feed, lamps, kFixtureMap, FeedSettings(), {native});
    const bool yields = !HasLamp(beside, lamps.besideNative) && HasLamp(beside, lamps.flame) &&
                        Candidate(beside, native.nativeId) && !feed.HeldBack(lamps.besideNative) &&
                        feed.Counts().heldBack == 0 && feed.Counts().offered == 3;
    bool waits = true;
    for (uint32_t capture = 2; capture < kLampHoldCaptures; ++capture)
    {
        const LocalLightInputs again = Offered(feed, lamps, kFixtureMap, FeedSettings(), {native});
        waits = waits && !HasLamp(again, lamps.besideNative) && !feed.HeldBack(lamps.besideNative);
    }
    Offered(feed, lamps, kFixtureMap, FeedSettings(), {native});
    const bool held = feed.HeldBack(lamps.besideNative) && feed.Counts().heldBack == 1;
    bool keptBack = true;
    for (int frame = 0; frame < 30; ++frame)
    {
        const LocalLightInputs alone = Offered(feed, lamps, kFixtureMap, FeedSettings());
        keptBack = keptBack && !HasLamp(alone, lamps.besideNative) && HasLamp(alone, lamps.flame) &&
                   feed.Counts().heldBack == 1;
    }
    Check(yields && waits && held && keptBack,
          "a lamp within 3 yd of a native light in the pool yields to it; once that light has rested beside it for "
          "60 captures the lamp is held back, and stays held back after that light leaves the pool, so the two "
          "cannot take turns");

    const LocalLightInputs otherMap = Offered(feed, lamps, kGridMap, FeedSettings());
    const bool reset = HasLamp(otherMap, lamps.otherMap) && feed.Counts().heldBack == 0 &&
                       !feed.HeldBack(lamps.besideNative) && feed.Counts().mapLamps == 1;
    const LocalLightInputs back = Offered(feed, lamps, kFixtureMap, FeedSettings());
    Check(reset && HasLamp(back, lamps.besideNative) && feed.Counts().heldBack == 0,
          "a map change resets the lamps held back, so the lamp is offered again once the map is entered anew");
}

constexpr float kPassingLampHeight = 40.0f;
constexpr float kPassingRunYards = 20.0f;
constexpr float kPassingSideYards = 1.0f;
constexpr float kMissileYardsPerCapture = 30.0f / 60.0f;
constexpr float kWalkerYardsPerCapture = 2.5f / 144.0f;

void BuildPassingCatalog(LampCatalog& catalog)
{
    Parses(catalog, LampFileBytes({{static_cast<uint32_t>(kFixtureMap),
                                    {FixtureLamp(0.0f, 0.0f, kPassingLampHeight, kLampRouteFlame)}}},
                                  {}));
}

struct PassingLight
{
    uint32_t captures = 0;
    uint32_t beside = 0;
    uint32_t offeredAway = 0;
    bool heldBack = false;
    bool offeredAfter = false;
};

PassingLight LightPassingTheLamp(float yardsPerCapture)
{
    LampCatalog catalog;
    BuildPassingCatalog(catalog);
    LampFeed feed;
    const LocalLightCamera camera = LampCamera();
    PassingLight result;
    const uint32_t steps = static_cast<uint32_t>(2.0f * kPassingRunYards / yardsPerCapture);
    for (uint32_t step = 0; step <= steps; ++step)
    {
        const float x = -kPassingRunYards + yardsPerCapture * static_cast<float>(step);
        LocalLightInputs inputs = WalkedNatives({NativeLight(0, x, kPassingSideYards, kPassingLampHeight)}, camera);
        feed.Offer(catalog, kFixtureMap, camera, kPlainUpload, FeedSettings(), inputs);
        const bool beside = x * x + kPassingSideYards * kPassingSideYards <=
                            kLampBesideNativeYards * kLampBesideNativeYards;
        ++result.captures;
        result.beside += beside ? 1 : 0;
        result.offeredAway += !beside && HasLamp(inputs, 0) ? 1 : 0;
    }
    LocalLightInputs after = WalkedNatives({}, camera);
    feed.Offer(catalog, kFixtureMap, camera, kPlainUpload, FeedSettings(), after);
    result.heldBack = feed.HeldBack(0);
    result.offeredAfter = HasLamp(after, 0);
    return result;
}

bool HeldBesideRestingLight(bool missilePasses)
{
    LampCatalog catalog;
    BuildPassingCatalog(catalog);
    LampFeed feed;
    const LocalLightCamera camera = LampCamera();
    const LocalPointLight resting = NativeLight(0, kPassingSideYards, kPassingSideYards, kPassingLampHeight);
    const float missileStart = -kMissileYardsPerCapture * static_cast<float>(kLampHoldCaptures / 2);
    bool heldEarly = false;
    bool yielded = true;
    for (uint32_t capture = 1; capture <= kLampHoldCaptures; ++capture)
    {
        std::vector<LocalPointLight> natives = {resting};
        if (missilePasses)
            natives.push_back(NativeLight(1, missileStart + kMissileYardsPerCapture * static_cast<float>(capture),
                                          -0.5f * kPassingSideYards, kPassingLampHeight));
        LocalLightInputs inputs = WalkedNatives(natives, camera);
        feed.Offer(catalog, kFixtureMap, camera, kPlainUpload, FeedSettings(), inputs);
        yielded = yielded && !HasLamp(inputs, 0);
        heldEarly = heldEarly || (capture < kLampHoldCaptures && feed.HeldBack(0));
    }
    return yielded && !heldEarly && feed.HeldBack(0) && feed.Counts().heldBack == 1;
}

void CheckFeedLetsPassingNativeLightsBy()
{
    const PassingLight missile = LightPassingTheLamp(kMissileYardsPerCapture);
    const PassingLight walker = LightPassingTheLamp(kWalkerYardsPerCapture);
    std::printf("     passing lights: a missile within 3 yd for %u of %u captures, a walker for %u of %u\n",
                missile.beside, missile.captures, walker.beside, walker.captures);
    const auto letBy = [](const PassingLight& light) {
        return light.beside > 0 && light.offeredAway == light.captures - light.beside && !light.heldBack &&
               light.offeredAfter;
    };
    Check(letBy(missile) && letBy(walker) && walker.beside > kLampHoldCaptures,
          "a light flying past a lamp at 30 yd/s, or carried past at walking pace at 144 frames a second, makes the "
          "lamp yield only while it is within 3 yd and never holds it back");
    Check(HeldBesideRestingLight(false) && HeldBesideRestingLight(true),
          "a light resting beside a lamp holds it back after 60 captures, even while another light flies past it");
}

void CheckFeedSettings()
{
    FeedCatalog lamps;
    BuildFeedCatalog(lamps);
    LampFeed feed;
    const std::vector<LocalPointLight> natives = {NativeLight(0, 20.0f, 0.0f, 50.0f)};
    const LocalLightInputs walked = WalkedNatives(natives, LampCamera());
    const LocalLightInputs off = Offered(feed, lamps, kFixtureMap, FeedSettings(false), natives);
    Check(off.candidateCount == walked.candidateCount && off.pointLightCount == walked.pointLightCount &&
              std::memcmp(off.candidates, walked.candidates, sizeof(walked.candidates)) == 0 &&
              std::memcmp(off.pointLights, walked.pointLights, sizeof(walked.pointLights)) == 0 &&
              feed.Counts().offered == 0 && feed.Counts().nearby == 0,
          "LampData=0 offers no lamp and leaves the native lights as walked");

    const LocalLightInputs bright = Offered(feed, lamps, kFixtureMap, FeedSettings(true, 2.5f));
    const LocalPointLight* flame = Candidate(bright, CatalogLampIdOf(lamps.flame));
    const LocalPointLight* named = Candidate(bright, CatalogLampIdOf(lamps.named));
    const LocalLightInputs dark = Offered(feed, lamps, kFixtureMap, FeedSettings(true, 0.0f));
    Check(flame && named && flame->color[0] == 1.0f && LocalNear(flame->color[1], 0.6f) &&
              LocalNear(flame->uploadedColor[0], 2.5f) && LocalNear(flame->uploadedColor[1], 0.6f * 2.5f) &&
              LocalNear(named->uploadedColor[0], 0.8f * 2.5f) &&
              CatalogLampsAmong(dark.candidates, dark.candidateCount) == 0,
          "LampIntensity scales each lamp's uploaded colour and keeps its catalogue colour, and 0 lets no lamp into "
          "the pool");

    const PointLightUpload linear = {true, 1.0f, 1.0f};
    const PointLightUpload dimmedClient = {true, 0.5f, 1.0f};
    const LocalLightInputs linearFull = Offered(feed, lamps, kFixtureMap, FeedSettings(true, 1.0f), {}, linear);
    const LocalLightInputs linearHalf = Offered(feed, lamps, kFixtureMap, FeedSettings(true, 0.5f), {}, linear);
    const LocalLightInputs clientHalf =
        Offered(feed, lamps, kFixtureMap, FeedSettings(true, 1.0f), {}, dimmedClient);
    const LocalPointLight* full = Candidate(linearFull, CatalogLampIdOf(lamps.named));
    const LocalPointLight* half = Candidate(linearHalf, CatalogLampIdOf(lamps.named));
    const LocalPointLight* client = Candidate(clientHalf, CatalogLampIdOf(lamps.named));
    bool linearFactor = full && half && client && full->uploadedColor[0] < 0.8f;
    for (int channel = 0; linearFactor && channel < 3; ++channel)
        linearFactor = LocalNear(half->uploadedColor[channel], 0.5f * full->uploadedColor[channel]) &&
                       half->uploadedColor[channel] == client->uploadedColor[channel];
    if (full && half)
        std::printf("     linear light: a lamp of peak 0.8 uploads %.4f at LampIntensity 1 and %.4f at 0.5\n",
                    full->uploadedColor[0], half->uploadedColor[0]);
    Check(linearFactor,
          "in linear light LampIntensity 0.5 halves a dim lamp's uploaded colour, exactly as LocalLightIntensity "
          "0.5 does, instead of darkening it to about a fifth");

    const LocalLightInputs within50 = Offered(feed, lamps, kFixtureMap, FeedSettings(true, 1.0f, 50.0f));
    const uint32_t offeredWithin50 = feed.Counts().offered;
    const LocalLightInputs within1000 = Offered(feed, lamps, kFixtureMap, FeedSettings(true, 1.0f, 1000.0f));
    Check(HasLamp(within50, lamps.flame) && HasLamp(within50, lamps.named) &&
              !HasLamp(within50, lamps.besideNative) && offeredWithin50 == 2 && HasLamp(within1000, lamps.distant) &&
              HasLamp(within1000, lamps.besideNative) && feed.Counts().offered == 5,
          "LampDistance bounds the lamps offered by their distance from the camera");

    LocalLightInputs unsupported;
    unsupported.capture = LocalLightCapture::UnsupportedClient;
    feed.Offer(lamps.catalog, kFixtureMap, LampCamera(), kPlainUpload, FeedSettings(), unsupported);
    Check(unsupported.candidateCount == 0 && feed.Counts().offered == 0,
          "no lamp is offered while the client's lights cannot be read at all");
}

constexpr int kDenseLampsPerSide = 41;
constexpr float kDenseLampSpacing = 5.0f;
constexpr uint32_t kDenseNatives = 30;
constexpr float kDenseNativeOffPlane = 4.0f;

std::vector<CatalogLamp> DenseLamps()
{
    std::vector<CatalogLamp> lamps;
    for (int i = 0; i < kDenseLampsPerSide; ++i)
        for (int j = 0; j < kDenseLampsPerSide; ++j)
            lamps.push_back(FixtureLamp(-100.0f + kDenseLampSpacing * static_cast<float>(i), 0.0f,
                                        10.0f + kDenseLampSpacing * static_cast<float>(j),
                                        static_cast<uint8_t>(kLampRouteAuthored + (i * 3 + j) % 5), kLampKindTorch,
                                        0.3f + 0.2f * static_cast<float>((i * 7 + j * 3) % 10)));
    return lamps;
}

std::vector<LocalPointLight> DenseNatives()
{
    std::vector<LocalPointLight> natives;
    for (uint32_t i = 0; i < kDenseNatives; ++i)
        natives.push_back(NativeLight(i, -30.0f + 2.0f * static_cast<float>(i), kDenseNativeOffPlane,
                                      12.0f + 4.0f * static_cast<float>(i), 1.5f));
    return natives;
}

LocalLightInputs EveryLampRanked(const LampCatalog& catalog, const LocalLightCamera& camera,
                                 const PointLightUpload& upload, const LampFeedSettings& settings)
{
    LocalLightInputs inputs = WalkedNatives(DenseNatives(), camera, upload);
    const PointLightUpload lampUpload = CatalogLampUpload(upload, settings.intensity);
    const auto rank = [&](const CatalogLamp& lamp, uint32_t mapLampIndex) {
        if (lamp.route != kLampRouteAuthored)
            engine::SelectLocalPointLightInView(inputs, CatalogPointLight(lamp, mapLampIndex), camera, lampUpload);
    };
    catalog.VisitLampsWithin(kFixtureMap, camera.position, settings.distance, rank);
    return inputs;
}

bool SameRanking(const LocalLightInputs& a, const LocalLightInputs& b)
{
    return a.candidateCount == b.candidateCount && a.pointLightCount == b.pointLightCount &&
           std::memcmp(a.candidates, b.candidates, sizeof(a.candidates)) == 0 &&
           std::memcmp(a.pointLights, b.pointLights, sizeof(a.pointLights)) == 0;
}

void CheckFeedSkipsLampsAFullPoolOutranks()
{
    LampCatalog catalog;
    Parses(catalog, LampFileBytes({{static_cast<uint32_t>(kFixtureMap), DenseLamps()}}, {}));
    const PointLightUpload uploads[] = {{false, 1.0f, 1.0f}, {true, 0.8f, 1.0f}};
    const LampFeedSettings settings = FeedSettings(true, 1.5f, 250.0f);
    LampFeed feed;
    bool same = true;
    bool counted = true;
    uint32_t nearby = 0;
    uint32_t outranked = 0;
    uint32_t pooled = 0;
    for (const PointLightUpload& upload : uploads)
        for (int step = 0; step < 5; ++step)
        {
            LocalLightCamera camera = LampCamera();
            camera.position[0] = -40.0f + 20.0f * static_cast<float>(step);
            LocalLightInputs offered = WalkedNatives(DenseNatives(), camera, upload);
            feed.Offer(catalog, kFixtureMap, camera, upload, settings, offered);
            const LampFeedCounts& counts = feed.Counts();
            same = same && SameRanking(offered, EveryLampRanked(catalog, camera, upload, settings));
            counted = counted && counts.offered + counts.outranked == counts.nearby && counts.pooled > 0;
            nearby += counts.nearby;
            outranked += counts.outranked;
            pooled += counts.pooled;
        }
    std::printf("     full pool: %u lamps near the camera over 10 captures, %u of them outranked before the ranking, "
                "%u pooled\n",
                nearby, outranked, pooled);
    Check(same && counted && outranked * 4 > nearby * 3,
          "lamps that a full light pool outranks are dropped before the full ranking, and the pool and the uploaded "
          "lights come out exactly as if every lamp had been ranked, in gamma and in linear light");
}

void CheckCalibrationAgainstNativeLights()
{
    LampCatalog catalog;
    Parses(catalog, LampFileBytes({{static_cast<uint32_t>(kFixtureMap),
                                    {FixtureLamp(10.0f, 10.0f, 10.0f, kLampRouteAuthored),
                                     FixtureLamp(40.0f, 10.0f, 10.0f, kLampRouteAuthored),
                                     FixtureLamp(70.0f, 10.0f, 10.0f, kLampRouteAuthored),
                                     FixtureLamp(100.0f, 10.0f, 10.0f, kLampRouteFlame)}}},
                                  {}));
    LocalPointLight natives[] = {NativeLight(0, 10.3f, 10.0f, 10.0f), NativeLight(1, 40.0f, 10.8f, 10.0f),
                                 NativeLight(2, 70.0f, 10.0f, 12.0f), NativeLight(3, 100.2f, 10.0f, 10.0f),
                                 NativeLight(4, 500.0f, 10.0f, 10.0f)};
    natives[0].attenuation[1] = 0.5f;
    const LampCalibration calibration = CalibrateLampData(catalog, kFixtureMap, natives, 5);
    std::printf("     calibration: %u of %u native lights matched, %u within 5 yd, median %.3f yd\n",
                calibration.matched, calibration.natives, calibration.nearby, calibration.medianOffset);
    Check(calibration.natives == 5 && calibration.matched == 2 && calibration.nearby == 3 &&
              LocalNear(calibration.medianOffset, 0.8f) && calibration.hasAttenuation &&
              calibration.attenuation[1] == 0.5f && calibration.attenuation[2] == kClientPointLightQuadraticAttenuation,
          "the calibration counts native lights with an authored lamp within 1 yd, takes the median offset of the "
          "nearest within 5 yd, ignores other routes and reports the first native light's attenuation");
}

struct LampFrames
{
    LampFeed feed;
    LocalLightStabiliser stabiliser;
    uint32_t frame = 0;

    LocalLightInputs Step(const LampCatalog& catalog, const std::vector<LocalPointLight>& natives,
                          LocalLightCapture capture)
    {
        const LocalLightCamera camera = LampCamera();
        LocalLightInputs inputs = WalkedNatives(natives, camera);
        inputs.capture = capture;
        feed.Offer(catalog, kFixtureMap, camera, kPlainUpload, FeedSettings(), inputs);
        ++frame;
        stabiliser.Step(camera, kFixtureMap, frame, frame * static_cast<double>(kLampFrameSeconds), inputs);
        return inputs;
    }
};

bool UploadsAtFullStrength(const LocalLightInputs& inputs, uintptr_t id)
{
    for (uint32_t i = 0; i < inputs.pointLightCount; ++i)
        if (inputs.pointLights[i].nativeId == id)
            return inputs.pointLights[i].uploadedColor[0] == inputs.pointLights[i].color[0];
    return false;
}

void CheckFailedWalkWithLampsHoldsTheLastSet()
{
    LampCatalog catalog;
    Parses(catalog, LampFileBytes({{static_cast<uint32_t>(kFixtureMap),
                                    {FixtureLamp(3.0f, 0.0f, 25.0f, kLampRouteFlame),
                                     FixtureLamp(-3.0f, 0.0f, 35.0f, kLampRouteEmissive)}}},
                                  {}));
    const std::vector<LocalPointLight> natives = {NativeLight(0, 0.0f, 0.0f, 20.0f),
                                                  NativeLight(1, 8.0f, 0.0f, 30.0f)};
    LampFrames frames;
    LocalLightInputs settled;
    for (int frame = 0; frame <= kLampFadeFrames; ++frame)
        settled = frames.Step(catalog, natives, LocalLightCapture::Captured);
    bool held = settled.pointLightCount == 4 && CatalogLampsAmong(settled.pointLights, 4) == 2;
    for (LocalLightCapture failure :
         {LocalLightCapture::TableChanged, LocalLightCapture::DamagedTable, LocalLightCapture::ReadFault})
    {
        const LocalLightInputs failed = frames.Step(catalog, {}, failure);
        held = held && failed.candidateCount == 2 && failed.pointLightCount == settled.pointLightCount &&
               std::memcmp(failed.pointLights, settled.pointLights, sizeof(settled.pointLights)) == 0;
    }
    const LocalLightInputs resumed = frames.Step(catalog, natives, LocalLightCapture::Captured);
    Check(held && frames.stabiliser.Activity().heldCaptures == 3 &&
              UploadsAtFullStrength(resumed, natives[0].nativeId) &&
              UploadsAtFullStrength(resumed, natives[1].nativeId),
          "a failed table walk that found no native light holds the last uploaded set although lamps from "
          "lampdata.bin are in the pool, and the native lights shine on at full strength once the walk recovers");
}

bool SameUploadedIds(const LocalLightInputs& a, const LocalLightInputs& b)
{
    if (a.pointLightCount != b.pointLightCount)
        return false;
    for (uint32_t i = 0; i < a.pointLightCount; ++i)
    {
        bool found = false;
        for (uint32_t j = 0; j < b.pointLightCount; ++j)
            found = found || a.pointLights[i].nativeId == b.pointLights[j].nativeId;
        if (!found)
            return false;
    }
    return true;
}

void CheckLampKeepsItsSlotBesideNativeLights()
{
    LampCatalog catalog;
    Parses(catalog, LampFileBytes({{static_cast<uint32_t>(kFixtureMap),
                                    {FixtureLamp(1.0f, 0.0f, 26.0f, kLampRouteFlame)}}},
                                  {}));
    const uintptr_t lampId = CatalogLampIdOf(0);
    std::vector<LocalPointLight> natives;
    for (uint32_t i = 0; i < 8; ++i)
        natives.push_back(NativeLight(i, 6.0f * (static_cast<float>(i % 3) - 1.0f), 4.0f,
                                      20.0f + 1.6f * static_cast<float>(i)));
    LampFrames frames;
    bool steady = true;
    bool churns = false;
    LocalLightInputs previous;
    for (int frame = 0; frame < 600; ++frame)
    {
        natives[6].color[0] = frame % 2 ? 1.3f : 0.7f;
        natives[7].color[0] = frame % 2 ? 0.7f : 1.3f;
        LocalLightInputs instant = WalkedNatives(natives, LampCamera());
        frames.feed.Offer(catalog, kFixtureMap, LampCamera(), kPlainUpload, FeedSettings(), instant);
        churns = churns || (frame > 0 && !SameUploadedIds(instant, previous));
        previous = instant;
        const LocalLightInputs stabilised = frames.Step(catalog, natives, LocalLightCapture::Captured);
        steady = steady && stabilised.pointLightCount == kMaxLocalPointLights &&
                 UploadsAtFullStrength(stabilised, lampId);
    }
    const LocalLightActivity& activity = frames.stabiliser.Activity();
    Check(churns && steady && activity.admissions == kMaxLocalPointLights && activity.evictions == 0 &&
              activity.fadeOuts == 0,
          "a lamp from lampdata.bin offered every frame keeps one slot at full strength for ten seconds beside "
          "eight native lights whose last two trade places every frame");
}

constexpr size_t kPythonFixtureBytes = 764;
constexpr int kPythonFixtureOutland = 530;

CatalogLamp StoredLamp(float x, float y, float z, float red, float green, float blue, float reach, uint16_t flags,
                       uint8_t kind, uint8_t route)
{
    CatalogLamp lamp = {};
    lamp.position[0] = x;
    lamp.position[1] = y;
    lamp.position[2] = z;
    lamp.color[0] = red;
    lamp.color[1] = green;
    lamp.color[2] = blue;
    lamp.reach = reach;
    lamp.flags = flags;
    lamp.kind = kind;
    lamp.route = route;
    return lamp;
}

std::vector<MapLamps> PythonFixtureMaps()
{
    return {{static_cast<uint32_t>(kFixtureMap),
             {StoredLamp(-17066.5f, 17060.25f, -250.0f, 0.6f, 0.35f, 0.1f, 6.0f, 0, kLampKindCandle, kLampRouteFlame),
              StoredLamp(-9000.25f, 400.5f, 60.0f, 2.0f, 1.25f, 0.5f, 16.0f, kLampFlagClampedToModel, kLampKindBrazier,
                         kLampRouteFlame),
              StoredLamp(-8833.5f, 622.25f, 93.75f, 1.0f, 0.75f, 0.5f, 12.0f, 0, kLampKindLamp, kLampRouteAuthored),
              StoredLamp(-8830.0f, 625.5f, 94.0f, 0.5f, 0.25f, 0.125f, 8.5f, kLampFlagDeadAuthoredBlocks,
                         kLampKindTorch, kLampRouteRestored),
              StoredLamp(-4981.25f, -881.5f, 501.75f, 1.5f, 1.125f, 0.625f, 12.0f,
                         kLampFlagWmoDoodad | kLampFlagBoundsFallback, kLampKindLamp, kLampRouteName),
              StoredLamp(-4981.0f, -881.0f, 505.0f, 0.75f, 0.5f, 0.25f, 6.0f, kLampFlagWmoDoodad, kLampKindChandelier,
                         kLampRouteEmissive)}},
            {static_cast<uint32_t>(kPythonFixtureOutland),
             {StoredLamp(-1838.5f, 5302.0f, -12.0f, 3.0f, 1.5f, 0.75f, 24.0f, kLampFlagGlobalWmo, kLampKindBonfire,
                         kLampRouteFlame),
              StoredLamp(-1838.0f, 5301.5f, -12.25f, 0.625f, 0.75f, 1.0f, 6.0f, 0, kLampKindCandle, kLampRouteName),
              StoredLamp(-248.5f, 932.25f, 84.5f, 1.0f, 0.5f, 0.0f, 20.0f, 0, kLampKindTorch, kLampRouteAuthored),
              StoredLamp(3000.0f, 2000.0f, 150.0f, 64.0f, 32.0f, 0.0f, 200.0f, 0, kLampKindUnknown,
                         kLampRouteRestored)}}};
}

const std::vector<std::string> kPythonFixtureSources = {
    "common.MPQ", "enUS\\patch-enUS-3.MPQ", "patch-A.MPQ",
    "enUS\\patch-enUS-Z-with-a-rather-long-name-for-the-sixty-three-byte-cut.MPQ"};
const std::vector<uint64_t> kPythonFixtureSourceSizes = {2919102541ull, 123456ull, 5000000000ull, 77ull};

std::vector<unsigned char> FileBytes(const std::string& path)
{
    std::vector<unsigned char> bytes;
    std::FILE* f = std::fopen(path.c_str(), "rb");
    if (!f)
        return bytes;
    unsigned char buffer[4096];
    for (size_t read; (read = std::fread(buffer, 1, sizeof(buffer), f)) > 0;)
        bytes.insert(bytes.end(), buffer, buffer + read);
    std::fclose(f);
    return bytes;
}

bool SameLamp(const CatalogLamp& a, const CatalogLamp& b)
{
    return std::memcmp(&a, &b, sizeof(CatalogLamp)) == 0;
}

bool StoredInOrder(const LampCatalog& catalog, const MapLamps& map)
{
    bool same = catalog.MapLampCount(static_cast<int>(map.mapId)) == map.lamps.size();
    for (size_t i = 0; same && i < map.lamps.size(); ++i)
    {
        const CatalogLamp& expected = map.lamps[i];
        const uint32_t index = IndexAt(catalog, static_cast<int>(map.mapId), expected.position[0],
                                       expected.position[1], expected.position[2]);
        const std::vector<VisitedLamp> found =
            LampsWithin(catalog, static_cast<int>(map.mapId), expected.position[0], expected.position[1],
                        expected.position[2], 0.0f);
        same = index == i && found.size() == 1 && SameLamp(found[0].lamp, expected);
    }
    return same;
}

void CheckLampDataFixtureFile(const std::string& path)
{
    const std::vector<unsigned char> bytes = FileBytes(path);
    LampCatalog catalog;
    const bool loaded = catalog.Load(path);
    std::printf("     %s: %zu bytes, %u maps, %u cells, %u lamps, %u sources%s%s\n", path.c_str(), bytes.size(),
                catalog.MapCount(), catalog.CellCount(), catalog.LampCount(), catalog.SourceCount(),
                catalog.Problem().empty() ? "" : ", ", catalog.Problem().c_str());
    Check(loaded && bytes.size() == kPythonFixtureBytes && catalog.MapCount() == 2 && catalog.CellCount() == 7 &&
              catalog.LampCount() == 10 && catalog.MapLampCount(kFixtureMap) == 6 &&
              catalog.MapLampCount(kPythonFixtureOutland) == 4 && catalog.RouteLampCount(kLampRouteAuthored) == 2 &&
              catalog.RouteLampCount(kLampRouteRestored) == 2 && catalog.RouteLampCount(kLampRouteFlame) == 3 &&
              catalog.RouteLampCount(kLampRouteName) == 2 && catalog.RouteLampCount(kLampRouteEmissive) == 1,
          "tests/data/lampdata-fixture.bin, written by tools/lamp_writer.py, loads with its two maps, seven cells "
          "and the lamps of every route");
    const bool sources = catalog.SourceCount() == 4 && catalog.Source(0).path == "common.MPQ" &&
                         catalog.Source(0).size == 2919102541ull &&
                         catalog.Source(1).path == "enUS\\patch-enUS-3.MPQ" && catalog.Source(1).size == 123456 &&
                         catalog.Source(2).path == "patch-A.MPQ" && catalog.Source(2).size == 5000000000ull &&
                         catalog.Source(3).path.size() == kLampSourcePathBytes - 1 &&
                         catalog.Source(3).path == kPythonFixtureSources[3].substr(0, kLampSourcePathBytes - 1) &&
                         catalog.Source(3).size == 77;
    const std::vector<MapLamps> expected = PythonFixtureMaps();
    Check(sources && StoredInOrder(catalog, expected[0]) && StoredInOrder(catalog, expected[1]) &&
              LampsWithin(catalog, kFixtureMap, -4981.0f, -881.0f, 503.0f, 5.0f).size() == 2 &&
              LampsWithin(catalog, kPythonFixtureOutland, 3000.0f, 2000.0f, 150.0f, 1.0f).size() == 1,
          "the Python writer's fixture keeps its archive names, a name cut to 63 bytes and a size above 4 GB, and "
          "every lamp's position, colour, reach, flags, kind, route and index within its map");
    Check(bytes == LampFileBytes(expected, kPythonFixtureSources, kPythonFixtureSourceSizes),
          "the Python writer and the harness lay out the same lamps, cells, maps and sources byte for byte");
}

void CheckLampData()
{
    CheckParserAcceptsTheFixture();
    CheckParserRejectsBrokenFiles();
    CheckRadiusQueryAcrossCells();
    CheckCatalogLampIds();
    CheckFeedOffersLampsWithoutAuthoredLights();
    CheckFeedHoldsBackLampsBesideNativeLights();
    CheckFeedLetsPassingNativeLightsBy();
    CheckFeedSettings();
    CheckFeedSkipsLampsAFullPoolOutranks();
    CheckCalibrationAgainstNativeLights();
    CheckFailedWalkWithLampsHoldsTheLastSet();
    CheckLampKeepsItsSlotBesideNativeLights();
}
}
