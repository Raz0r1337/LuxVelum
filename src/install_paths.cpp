#include "install_paths.h"

#include <windows.h>

namespace
{
constexpr const char* kLogFolder = "Logs";
constexpr const char* kSettingsFolder = "WTF";
constexpr const char* kLuxVelumDataFolder = "Data\\LuxVelum";
constexpr const char* kLogName = "LuxVelum.log";
constexpr const char* kIniName = "LuxVelum.ini";
constexpr const char* kFogDataName = "fogdata.bin";
constexpr const char* kWaterDataName = "waterdata.bin";

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
    const std::string inData = clientFolder + kLuxVelumDataFolder + "\\" + name;
    const std::string besideTheDll = clientFolder + name;
    return !IsFile(inData) && IsFile(besideTheDll) ? besideTheDll : inData;
}
}

InstallPaths ClientInstallPaths(const std::string& clientFolder)
{
    return {FolderOrClientFolder(clientFolder, kLogFolder) + kLogName,
            FolderOrClientFolder(clientFolder, kSettingsFolder) + kIniName, DataFile(clientFolder, kFogDataName),
            DataFile(clientFolder, kWaterDataName)};
}
