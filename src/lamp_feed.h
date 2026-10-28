#pragma once

#include "engine_lights.h"
#include "lamp_data.h"

#include <cstdint>
#include <vector>

constexpr float kClientPointLightConstantAttenuation = 0.0f;
constexpr float kClientPointLightLinearAttenuation = 0.7f;
constexpr float kClientPointLightQuadraticAttenuation = 0.03f;
constexpr float kLampBesideNativeYards = 3.0f;
constexpr uint32_t kLampHoldCaptures = 60;
constexpr float kLampStaticNativeYards = 0.25f;
constexpr float kLampCalibrationMatchYards = 1.0f;
constexpr float kLampCalibrationSearchYards = 5.0f;
constexpr double kLampFeedLogSeconds = 60.0;
constexpr uintptr_t kCatalogLampIdBit = 1;

constexpr bool CatalogLampId(uintptr_t id)
{
    return (id & kCatalogLampIdBit) != 0;
}

constexpr uintptr_t CatalogLampIdOf(uint32_t mapLampIndex)
{
    return (static_cast<uintptr_t>(mapLampIndex) << 1) | kCatalogLampIdBit;
}

struct LampFeedSettings
{
    bool enabled = true;
    float intensity = 1.0f;
    float distance = 250.0f;
};

struct LampFeedCounts
{
    uint32_t mapLamps = 0;
    uint32_t nearby = 0;
    uint32_t offered = 0;
    uint32_t outranked = 0;
    uint32_t heldBack = 0;
    uint32_t pooled = 0;
};

struct LampCalibration
{
    uint32_t natives = 0;
    uint32_t matched = 0;
    uint32_t nearby = 0;
    float medianOffset = 0.0f;
    bool hasAttenuation = false;
    float attenuation[3] = {};
};

LocalPointLight CatalogPointLight(const CatalogLamp& lamp, uint32_t mapLampIndex);
PointLightUpload CatalogLampUpload(const PointLightUpload& upload, float intensity);
uint32_t CatalogLampsAmong(const LocalPointLight* lights, uint32_t count);
LampCalibration CalibrateLampData(const LampCatalog& catalog, int mapId, const LocalPointLight* natives,
                                  uint32_t count);

class LampFeed
{
public:
    void Offer(const LampCatalog& catalog, int mapId, const LocalLightCamera& camera, const PointLightUpload& upload,
               const LampFeedSettings& settings, LocalLightInputs& lights);
    void LogActivity(const LampCatalog& catalog, double seconds);
    void Reset();
    const LampFeedCounts& Counts() const { return m_counts; }
    bool HeldBack(uint32_t mapLampIndex) const;

private:
    struct PendingHold
    {
        uint32_t mapLampIndex = 0;
        uintptr_t nativeId = 0;
        float anchor[3] = {};
        uint32_t captures = 0;
        uint32_t lastOffer = 0;
    };

    void StartMap(int mapId);
    void KeepNativeCandidates(const LocalLightInputs& lights);
    const LocalPointLight* NativeBeside(const CatalogLamp& lamp, uintptr_t preferredId) const;
    PendingHold* FindPendingHold(uint32_t mapLampIndex);
    PendingHold& AddPendingHold(uint32_t mapLampIndex);
    bool YieldsToNative(const CatalogLamp& lamp, uint32_t mapLampIndex);
    void HoldBack(uint32_t mapLampIndex);
    void DropStalePendingHolds();
    void PrepareLinearPeaks(const LampCatalog& catalog, uint32_t mapLamps);
    float UnscaledPeak(const CatalogLamp& lamp, uint32_t mapLampIndex, bool linear);
    void UpdatePoolFloor(const LocalLightInputs& lights, const float cameraPosition[3]);
    bool Outranked(const CatalogLamp& lamp, uint32_t mapLampIndex, const float cameraPosition[3],
                   const PointLightUpload& lampUpload);
    void OfferLamp(const CatalogLamp& lamp, uint32_t mapLampIndex, const LocalLightCamera& camera,
                   const PointLightUpload& lampUpload, LocalLightInputs& lights);
    void LogCalibration(const LampCatalog& catalog) const;

    std::vector<uint8_t> m_heldBack;
    uint32_t m_heldBackCount = 0;
    std::vector<PendingHold> m_pending;
    uint32_t m_offers = 0;
    std::vector<float> m_linearPeaks;
    const LampCatalog* m_peakCatalog = nullptr;
    bool m_poolFull = false;
    double m_poolFloor = 0.0;
    LocalPointLight m_natives[kLocalLightCandidatePool] = {};
    uint32_t m_nativeCount = 0;
    LampFeedCounts m_counts;
    LampFeedCounts m_loggedCounts;
    float m_distance = 0.0f;
    int m_mapId = 0;
    bool m_mapKnown = false;
    double m_lastLogSeconds = 0.0;
    bool m_logStarted = false;
};
