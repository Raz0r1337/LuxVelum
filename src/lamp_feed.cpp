#include "lamp_feed.h"

#include "log.h"

#include <algorithm>
#include <cmath>
#include <iterator>
#include <limits>

namespace
{
constexpr uintptr_t kNoNativeLight = 0;
constexpr float kUnknownLinearPeak = -1.0f;

double SquaredDistance(const float a[3], const float b[3])
{
    double sum = 0.0;
    for (int i = 0; i < 3; ++i)
    {
        const double delta = static_cast<double>(a[i]) - b[i];
        sum += delta * delta;
    }
    return sum;
}

float Median(std::vector<float> values)
{
    if (values.empty())
        return 0.0f;
    std::sort(values.begin(), values.end());
    const size_t middle = values.size() / 2;
    return values.size() % 2 ? values[middle] : 0.5f * (values[middle - 1] + values[middle]);
}

float NearestAuthoredLamp(const LampCatalog& catalog, int mapId, const LocalPointLight& native)
{
    double nearestSquared = std::numeric_limits<double>::infinity();
    const auto consider = [&](const CatalogLamp& lamp, uint32_t) {
        if (lamp.route == kLampRouteAuthored)
            nearestSquared = std::min(nearestSquared, SquaredDistance(lamp.position, native.position));
    };
    catalog.VisitLampsWithin(mapId, native.position, kLampCalibrationSearchYards, consider);
    return static_cast<float>(std::sqrt(nearestSquared));
}

bool SameCounts(const LampFeedCounts& a, const LampFeedCounts& b)
{
    return a.mapLamps == b.mapLamps && a.nearby == b.nearby && a.offered == b.offered &&
           a.outranked == b.outranked && a.heldBack == b.heldBack && a.pooled == b.pooled;
}

bool StaysAt(const LocalPointLight& native, const float anchor[3])
{
    const double staticSquared = static_cast<double>(kLampStaticNativeYards) * kLampStaticNativeYards;
    return SquaredDistance(native.position, anchor) <= staticSquared;
}

float PeakOf(const float color[3])
{
    return std::max(color[0], std::max(color[1], color[2]));
}

float UnscaledPeakOf(const CatalogLamp& lamp, bool linear)
{
    float uploaded[3];
    engine::UploadedPointLightColor(lamp.color, {linear, 1.0f, 1.0f}, uploaded);
    return PeakOf(uploaded);
}

double LampPriority(const CatalogLamp& lamp, float uploadedPeak, const float cameraPosition[3])
{
    LocalPointLight probe = CatalogPointLight(lamp, 0);
    std::fill(std::begin(probe.uploadedColor), std::end(probe.uploadedColor), uploadedPeak);
    return engine::LocalLightPriority(probe, cameraPosition);
}
}

LocalPointLight CatalogPointLight(const CatalogLamp& lamp, uint32_t mapLampIndex)
{
    LocalPointLight light;
    std::copy(lamp.position, lamp.position + 3, light.position);
    std::copy(lamp.color, lamp.color + 3, light.color);
    light.attenuation[0] = kClientPointLightConstantAttenuation;
    light.attenuation[1] = kClientPointLightLinearAttenuation;
    light.attenuation[2] = kClientPointLightQuadraticAttenuation;
    light.enabled = 1;
    light.nativeId = CatalogLampIdOf(mapLampIndex);
    return light;
}

PointLightUpload CatalogLampUpload(const PointLightUpload& upload, float intensity)
{
    return {upload.linear, upload.intensity * intensity, upload.reach};
}

uint32_t CatalogLampsAmong(const LocalPointLight* lights, uint32_t count)
{
    uint32_t lamps = 0;
    for (uint32_t i = 0; i < count; ++i)
        lamps += CatalogLampId(lights[i].nativeId) ? 1 : 0;
    return lamps;
}

LampCalibration CalibrateLampData(const LampCatalog& catalog, int mapId, const LocalPointLight* natives,
                                  uint32_t count)
{
    LampCalibration calibration;
    std::vector<float> offsets;
    for (uint32_t i = 0; i < count; ++i)
    {
        const LocalPointLight& native = natives[i];
        if (CatalogLampId(native.nativeId))
            continue;
        if (!calibration.hasAttenuation)
        {
            std::copy(native.attenuation, native.attenuation + 3, calibration.attenuation);
            calibration.hasAttenuation = true;
        }
        ++calibration.natives;
        const float nearest = NearestAuthoredLamp(catalog, mapId, native);
        if (!std::isfinite(nearest))
            continue;
        offsets.push_back(nearest);
        calibration.matched += nearest <= kLampCalibrationMatchYards ? 1 : 0;
    }
    calibration.nearby = static_cast<uint32_t>(offsets.size());
    calibration.medianOffset = Median(offsets);
    return calibration;
}

void LampFeed::Reset()
{
    m_heldBack.clear();
    m_heldBackCount = 0;
    m_pending.clear();
    m_linearPeaks.clear();
    m_peakCatalog = nullptr;
    m_nativeCount = 0;
    m_counts = {};
    m_mapKnown = false;
}

bool LampFeed::HeldBack(uint32_t mapLampIndex) const
{
    return mapLampIndex < m_heldBack.size() && m_heldBack[mapLampIndex];
}

void LampFeed::StartMap(int mapId)
{
    Reset();
    m_mapId = mapId;
    m_mapKnown = true;
}

void LampFeed::KeepNativeCandidates(const LocalLightInputs& lights)
{
    m_nativeCount = 0;
    const uint32_t count = std::min(lights.candidateCount, kLocalLightCandidatePool);
    for (uint32_t i = 0; i < count; ++i)
        if (!CatalogLampId(lights.candidates[i].nativeId))
            m_natives[m_nativeCount++] = lights.candidates[i];
}

const LocalPointLight* LampFeed::NativeBeside(const CatalogLamp& lamp, uintptr_t preferredId) const
{
    const double besideSquared = static_cast<double>(kLampBesideNativeYards) * kLampBesideNativeYards;
    const LocalPointLight* nearest = nullptr;
    double nearestSquared = besideSquared;
    for (uint32_t i = 0; i < m_nativeCount; ++i)
    {
        const double distanceSquared = SquaredDistance(lamp.position, m_natives[i].position);
        if (distanceSquared > besideSquared)
            continue;
        if (m_natives[i].nativeId == preferredId)
            return &m_natives[i];
        if (!nearest || distanceSquared < nearestSquared)
        {
            nearest = &m_natives[i];
            nearestSquared = distanceSquared;
        }
    }
    return nearest;
}

LampFeed::PendingHold* LampFeed::FindPendingHold(uint32_t mapLampIndex)
{
    for (PendingHold& pending : m_pending)
        if (pending.mapLampIndex == mapLampIndex)
            return &pending;
    return nullptr;
}

LampFeed::PendingHold& LampFeed::AddPendingHold(uint32_t mapLampIndex)
{
    m_pending.emplace_back();
    m_pending.back().mapLampIndex = mapLampIndex;
    return m_pending.back();
}

bool LampFeed::YieldsToNative(const CatalogLamp& lamp, uint32_t mapLampIndex)
{
    PendingHold* pending = FindPendingHold(mapLampIndex);
    const LocalPointLight* native = NativeBeside(lamp, pending ? pending->nativeId : kNoNativeLight);
    if (!native)
        return false;
    if (!pending)
        pending = &AddPendingHold(mapLampIndex);
    if (native->nativeId != pending->nativeId || !StaysAt(*native, pending->anchor))
    {
        pending->nativeId = native->nativeId;
        std::copy(native->position, native->position + 3, pending->anchor);
        pending->captures = 0;
    }
    pending->lastOffer = m_offers;
    if (++pending->captures >= kLampHoldCaptures)
        HoldBack(mapLampIndex);
    return true;
}

void LampFeed::HoldBack(uint32_t mapLampIndex)
{
    if (mapLampIndex >= m_heldBack.size())
        m_heldBack.resize(static_cast<size_t>(mapLampIndex) + 1, 0);
    m_heldBack[mapLampIndex] = 1;
    ++m_heldBackCount;
}

void LampFeed::DropStalePendingHolds()
{
    const uint32_t offer = m_offers;
    m_pending.erase(std::remove_if(m_pending.begin(), m_pending.end(),
                                   [offer](const PendingHold& pending) { return pending.lastOffer != offer; }),
                    m_pending.end());
}

void LampFeed::PrepareLinearPeaks(const LampCatalog& catalog, uint32_t mapLamps)
{
    if (m_peakCatalog == &catalog && m_linearPeaks.size() == mapLamps)
        return;
    m_linearPeaks.assign(mapLamps, kUnknownLinearPeak);
    m_peakCatalog = &catalog;
}

float LampFeed::UnscaledPeak(const CatalogLamp& lamp, uint32_t mapLampIndex, bool linear)
{
    if (!linear || mapLampIndex >= m_linearPeaks.size())
        return UnscaledPeakOf(lamp, linear);
    float& peak = m_linearPeaks[mapLampIndex];
    if (peak < 0.0f)
        peak = UnscaledPeakOf(lamp, true);
    return peak;
}

void LampFeed::UpdatePoolFloor(const LocalLightInputs& lights, const float cameraPosition[3])
{
    m_poolFull = lights.candidateCount >= kLocalLightCandidatePool;
    m_poolFloor =
        m_poolFull ? engine::LocalLightPriority(lights.candidates[kLocalLightCandidatePool - 1], cameraPosition) : 0.0;
}

bool LampFeed::Outranked(const CatalogLamp& lamp, uint32_t mapLampIndex, const float cameraPosition[3],
                         const PointLightUpload& lampUpload)
{
    if (!m_poolFull)
        return false;
    const float uploadedPeak = UnscaledPeak(lamp, mapLampIndex, lampUpload.linear) * lampUpload.intensity;
    return LampPriority(lamp, uploadedPeak, cameraPosition) < m_poolFloor;
}

void LampFeed::OfferLamp(const CatalogLamp& lamp, uint32_t mapLampIndex, const LocalLightCamera& camera,
                         const PointLightUpload& lampUpload, LocalLightInputs& lights)
{
    if (lamp.route == kLampRouteAuthored)
        return;
    ++m_counts.nearby;
    if (HeldBack(mapLampIndex))
        return;
    if (Outranked(lamp, mapLampIndex, camera.position, lampUpload))
    {
        ++m_counts.outranked;
        return;
    }
    if (YieldsToNative(lamp, mapLampIndex))
        return;
    ++m_counts.offered;
    engine::SelectLocalPointLightInView(lights, CatalogPointLight(lamp, mapLampIndex), camera, lampUpload);
    UpdatePoolFloor(lights, camera.position);
}

void LampFeed::Offer(const LampCatalog& catalog, int mapId, const LocalLightCamera& camera,
                     const PointLightUpload& upload, const LampFeedSettings& settings, LocalLightInputs& lights)
{
    if (!m_mapKnown || mapId != m_mapId)
        StartMap(mapId);
    ++m_offers;
    m_counts = {};
    m_counts.mapLamps = catalog.MapLampCount(mapId);
    m_distance = settings.distance;
    KeepNativeCandidates(lights);
    if (settings.enabled && engine::CapturedLightsUsable(lights.capture))
    {
        const PointLightUpload lampUpload = CatalogLampUpload(upload, settings.intensity);
        PrepareLinearPeaks(catalog, m_counts.mapLamps);
        UpdatePoolFloor(lights, camera.position);
        const auto offer = [&](const CatalogLamp& lamp, uint32_t mapLampIndex) {
            OfferLamp(lamp, mapLampIndex, camera, lampUpload, lights);
        };
        catalog.VisitLampsWithin(mapId, camera.position, settings.distance, offer);
    }
    DropStalePendingHolds();
    m_counts.heldBack = m_heldBackCount;
    m_counts.pooled = CatalogLampsAmong(lights.candidates, std::min(lights.candidateCount, kLocalLightCandidatePool));
}

void LampFeed::LogActivity(const LampCatalog& catalog, double seconds)
{
    if (!m_logStarted || seconds < m_lastLogSeconds)
    {
        m_logStarted = true;
        m_lastLogSeconds = seconds;
        return;
    }
    if (seconds - m_lastLogSeconds < kLampFeedLogSeconds)
        return;
    m_lastLogSeconds = seconds;
    if (!LogEnabled(LogLevel::Debug) || SameCounts(m_counts, m_loggedCounts))
        return;
    m_loggedCounts = m_counts;
    VF_LOG_DEBUG("lamp data on map %d: %u lamps, %u of them not authored within %.0f yd, %u offered to the fog, %u "
                 "outranked by a full light pool, %u held back beside the client's own lights since the map loaded, "
                 "%u in the light pool",
                 m_mapId, m_counts.mapLamps, m_counts.nearby, m_distance, m_counts.offered, m_counts.outranked,
                 m_counts.heldBack, m_counts.pooled);
    LogCalibration(catalog);
}

void LampFeed::LogCalibration(const LampCatalog& catalog) const
{
    const LampCalibration calibration = CalibrateLampData(catalog, m_mapId, m_natives, m_nativeCount);
    if (!calibration.natives)
    {
        VF_LOG_DEBUG("lamp data calibration: no native light in the pool");
        return;
    }
    if (!calibration.nearby)
    {
        VF_LOG_DEBUG("lamp data calibration: none of %u native lights in the pool has an authored lamp within %.0f "
                     "yd; the first native light's attenuation is %.4g %.4g %.4g",
                     calibration.natives, kLampCalibrationSearchYards, calibration.attenuation[0],
                     calibration.attenuation[1], calibration.attenuation[2]);
        return;
    }
    VF_LOG_DEBUG("lamp data calibration: %u of %u native lights in the pool have an authored lamp within %.0f yd and "
                 "%u within %.0f yd, the nearest %.2f yd away at the median; the first native light's attenuation is "
                 "%.4g %.4g %.4g",
                 calibration.matched, calibration.natives, kLampCalibrationMatchYards, calibration.nearby,
                 kLampCalibrationSearchYards, calibration.medianOffset, calibration.attenuation[0],
                 calibration.attenuation[1], calibration.attenuation[2]);
}
