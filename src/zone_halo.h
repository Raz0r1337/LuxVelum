#pragma once

#include <map>
#include <string>

constexpr float kZoneHaloMax = 4.0f;
constexpr double kZoneHaloFadeSeconds = 0.6;
constexpr size_t kZoneNameSize = 64;

struct ZoneHaloFactors
{
    float sun = 1.0f;
    float moon = 1.0f;
};

struct ZoneHalo
{
    int zoneId = 0;
    float sun = 1.0f;
    float moon = 1.0f;
};

class ZoneHaloTable
{
public:
    void Load(const std::string& path);
    ZoneHaloFactors Factors(int zoneId) const;
    bool Listed(int zoneId) const { return m_factors.count(zoneId) != 0; }
    void Edit(int zoneId, const ZoneHaloFactors& factors);
    bool Save(int zoneId, const char* zoneName) const;
    bool Forget(int zoneId);
    int Count() const { return static_cast<int>(m_factors.size()); }
    const std::string& Path() const { return m_path; }

private:
    std::string m_path;
    std::map<int, ZoneHaloFactors> m_factors;
};

class ZoneHaloFade
{
public:
    ZoneHalo Advance(int zoneId, const ZoneHaloFactors& target, double seconds);

private:
    ZoneHalo m_current;
    double m_advancedTo = 0.0;
    bool m_started = false;
    bool m_fading = false;
};

struct ZoneHaloView
{
    int zoneId = 0;
    char zoneName[kZoneNameSize] = {};
    ZoneHaloFactors factors;
    bool listed = false;
};

class ZoneHaloBook
{
public:
    void Load(const std::string& path);
    ZoneHalo Advance(int zoneId, const char* zoneName, double seconds);
    ZoneHaloView Current() const;
    void Edit(const ZoneHaloFactors& factors);
    bool SaveCurrent();
    bool ForgetCurrent();
    const ZoneHaloTable& Table() const { return m_table; }

private:
    ZoneHaloTable m_table;
    ZoneHaloFade m_fade;
    ZoneHaloView m_view;
};

ZoneHaloBook& GlobalZoneHalo();
