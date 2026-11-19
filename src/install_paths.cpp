#include "install_paths.h"

#include <windows.h>

namespace
{
constexpr const char* kLogFolder = "Logs";
constexpr const char* kSettingsFolder = "WTF";
constexpr const char* kLuxvelumDataFolder = "Data\\Luxvelum";
constexpr const char* kLogName = "Luxvelum.log";
constexpr const char* kIniName = "Luxvelum.ini";
constexpr const char* kZoneHaloName = "Luxvelum-zones.ini";
constexpr const char* kFogDataName = "fogdata.bin";
constexpr const char* kWaterDataName = "waterdata.bin";
constexpr const char* kShippedZoneHaloName = "zones.ini";

bool IsFolder(const std::string& path)
{
    const DWORD attributes = GetFileAttributesA(path.c_str());
    return attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
}

bool IsFile(const std::string& path)
{
    const DWORD attributes = GetFileAttributesA(path.c_str());
    return attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_DIRECTORY) == 0;
}

std::string FolderOrClientFolder(const std::string& clientFolder, const char* folder)
{
    const std::string path = clientFolder + folder;
    CreateDirectoryA(path.c_str(), nullptr);
    return IsFolder(path) ? path + "\\" : clientFolder;
}

std::string DataFile(const std::string& clientFolder, const char* name)
{
    const std::string inData = clientFolder + kLuxvelumDataFolder + "\\" + name;
    const std::string besideTheDll = clientFolder + name;
    return !IsFile(inData) && IsFile(besideTheDll) ? besideTheDll : inData;
}
}

InstallPaths ClientInstallPaths(const std::string& clientFolder)
{
    const std::string settings = FolderOrClientFolder(clientFolder, kSettingsFolder);
    return {FolderOrClientFolder(clientFolder, kLogFolder) + kLogName, settings + kIniName,
            DataFile(clientFolder, kFogDataName), DataFile(clientFolder, kWaterDataName), settings + kZoneHaloName,
            DataFile(clientFolder, kShippedZoneHaloName)};
}
