#pragma once

namespace lamp_settings_checks
{
using forever_look_checks::ListsOnce;

void CheckShippedLampSettings(const std::wstring& shippedIni)
{
    ConfigStore shipped;
    shipped.Load(NarrowPath(shippedIni));
    const Config& s = shipped.Get();
    const std::string text = ReadText(shippedIni);
    const std::vector<std::string> lines = water_settings_checks::IniLines(text);
    const Config defaults;
    Check(s.lampData && s.lampIntensity == 1.0f && s.lampDistance == 250.0f && defaults.lampData &&
              defaults.lampIntensity == 1.0f && defaults.lampDistance == 250.0f && ListsOnce(lines, "LampData=1") &&
              ListsOnce(lines, "LampIntensity=1.0") && ListsOnce(lines, "LampDistance=250") &&
              text.find("; Lamps whose model carries no light of its own") != std::string::npos &&
              text.find("Data\\LuxVelum\\lampdata.bin") != std::string::npos &&
              text.find("; Brightness of those lamps in the fog, 0..8") != std::string::npos &&
              text.find("; How far from the camera those lamps are looked for, 50..1000 yd") != std::string::npos,
          "the shipped INI turns LampData on at LampIntensity 1 within LampDistance 250 yd and documents the three "
          "keys");
}

void CheckLampSettingsClampAndSave(const std::wstring& outDir, const std::wstring& shippedIni)
{
    const std::wstring lampIni = FullPath(outDir + L"\\lamps.ini");
    CopyFileW(shippedIni.c_str(), lampIni.c_str(), FALSE);
    WritePrivateProfileStringW(L"LuxVelum", L"LampData", L"0", lampIni.c_str());
    WritePrivateProfileStringW(L"LuxVelum", L"LampIntensity", L"20", lampIni.c_str());
    WritePrivateProfileStringW(L"LuxVelum", L"LampDistance", L"10", lampIni.c_str());
    ConfigStore low;
    low.Load(NarrowPath(lampIni));
    WritePrivateProfileStringW(L"LuxVelum", L"LampIntensity", L"-1", lampIni.c_str());
    WritePrivateProfileStringW(L"LuxVelum", L"LampDistance", L"5000", lampIni.c_str());
    ConfigStore high;
    high.Load(NarrowPath(lampIni));
    Check(!low.Get().lampData && low.Get().lampIntensity == kLampIntensityMax &&
              low.Get().lampDistance == kLampDistanceMin && high.Get().lampIntensity == 0.0f &&
              high.Get().lampDistance == kLampDistanceMax,
          "LampData, LampIntensity and LampDistance are read from the INI, intensity clamped to 0..8 and distance to "
          "50..1000 yd");

    ConfigStore store;
    store.Load(NarrowPath(shippedIni));
    const Config shipped = store.Get();
    Config edited = shipped;
    edited.lampData = false;
    edited.lampIntensity = 2.5f;
    edited.lampDistance = 400.0f;
    Config intensityOnly = shipped;
    intensityOnly.lampIntensity = 2.5f;
    Config distanceOnly = shipped;
    distanceOnly.lampDistance = 400.0f;
    Config switchedOff = shipped;
    switchedOff.lampData = false;
    const std::string changes = SettingChanges(shipped, edited);
    std::printf("     lamp setting changes log \"%s\"\n", changes.c_str());
    Check(changes == "LampIntensity 1 -> 2.5, LampDistance 250 -> 400, LampData 1 -> 0" &&
              !SameFogSettings(shipped, intensityOnly) && !SameFogSettings(shipped, distanceOnly) &&
              !SameFogSettings(shipped, switchedOff),
          "lamp setting changes are logged and discard the fog history like the other local-light settings");

    const std::wstring savedIni = FullPath(outDir + L"\\lamps-saved.ini");
    CopyFileW(shippedIni.c_str(), savedIni.c_str(), FALSE);
    ConfigStore saving;
    saving.Load(NarrowPath(savedIni));
    Config clamped = edited;
    clamped.lampIntensity = 99.0f;
    saving.Apply(clamped);
    const bool appliedClamped = saving.Get().lampIntensity == kLampIntensityMax;
    saving.Apply(edited);
    const bool saved = saving.Save();
    ConfigStore reloaded;
    reloaded.Load(NarrowPath(savedIni));
    const std::string savedText = ReadText(savedIni);
    const std::vector<std::string> savedLines = water_settings_checks::IniLines(savedText);
    Check(appliedClamped && saved && !reloaded.Get().lampData && reloaded.Get().lampIntensity == 2.5f &&
              reloaded.Get().lampDistance == 400.0f && ListsOnce(savedLines, "LampData=0") &&
              ListsOnce(savedLines, "LampIntensity=2.5") && ListsOnce(savedLines, "LampDistance=400") &&
              savedText.find("; Lamps whose model carries no light of its own") != std::string::npos,
          "the settings window clamps LampIntensity, and saves and reloads the three lamp settings in place, keeping "
          "their comments");
}

void CheckLampSettings(const std::wstring& outDir, const std::wstring& shippedIni)
{
    CheckShippedLampSettings(shippedIni);
    CheckLampSettingsClampAndSave(outDir, shippedIni);
}
}
