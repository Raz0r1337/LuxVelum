#pragma once

#include "ps_lit_split_composite_low.h"
#include "ps_lit_split_composite_high.h"

namespace halo_occlusion
{
constexpr UINT kSize = 64;
constexpr int kConstantRegisters = 99;
constexpr int kLightRegister = 9;
constexpr int kLightShadowRegister = 10;
constexpr int kMarchRegister = 11;
constexpr int kFirstLayerRegister = 12;
constexpr float kDepthAtInfiniteViewZ = 0.940376f;
constexpr float kDepthPerInverseViewZ = -0.3761504f;
constexpr float kDeepestWorldDepth = 0.94f;
constexpr float kSkyDepth = 1.0f;
constexpr float kSkyMinDepth = 0.99903f;
constexpr float kDistantTerrainDepth = 0.9985f;
constexpr float kMaxFogDistance = 5000.0f;
constexpr float kDistanceCurveRange = 1000.0f;
constexpr float kHorizonBlendStart = 850.0f;
constexpr float kFarClip = 1000.0f;
constexpr float kGroundViewY = -10.0f;
constexpr float kNoHit = 1.0e30f;
constexpr float kParallelRay = 1.0e-12f;
constexpr float kLayerDensity = 0.003f;
constexpr float kLayerPhaseG = 0.6f;
constexpr float kLayerEmissive[3] = {0.04f, 0.05f, 0.06f};
constexpr float kLayerDiffuse[3] = {1.0f, 0.9f, 0.8f};
constexpr Vec3 kToLightAhead = {0.15f, 0.25f, 1.0f};
constexpr Vec3 kToLightBehind = {0.15f, 0.25f, -1.0f};
constexpr float kHalfStrength = 0.5f;
constexpr float kJitterFrame = 17.0f;
constexpr float kLoopedJitterFrame = 5.0f;
constexpr float kMinDirectRadiance = 1.0e-6f;
constexpr float kMaxDirectShareBehindSolid = 0.15f;
constexpr float kMaxGapLoss = 0.01f;
constexpr float kMinLossBesideTrunk = 0.02f;
constexpr float kMaxLossBesideTrunk = 0.3f;
constexpr float kMaxGroundLoss = 0.05f;
constexpr float kMaxMeanGroundLoss = 0.005f;
constexpr float kMaxUnshadowedChange = 1.0e-5f;
constexpr float kMaxLinearityError = 1.0e-4f;
constexpr float kMaxLoopedDifference = 1.0e-4f;
constexpr float kMaxOpacityChange = 1.0e-6f;
constexpr float kMaxConstantError = 1.0e-4f;
constexpr float kLightInPictureViewZ = 0.9f;
constexpr float kRampMidViewZ = 0.125f;
constexpr float kBelowFrontViewZ = 0.04f;
constexpr int kRampSamples = 16;
constexpr float kHalfInteriorBlend = 0.5f;
constexpr float kMoonScatterOff = 0.0f;
constexpr float kMoonScatterOn = 0.2f;
constexpr float kFlaggedLayerDensity = 0.001f;
constexpr float kHalfAboveHorizon = 0.5f;
constexpr float kWallDistance = 180.0f;
constexpr int kMinSunCodes = 3;
constexpr float kMaxSunShareBehindWall = 0.5f;
constexpr float kMaxUnshadowedLoss = 1.0e-5f;
constexpr float kMinSkyLossAboveRidge = 0.2f;
constexpr float kFarProjectionScale = 4.0f;
constexpr float kThinLayerDensity = 0.00013f;
constexpr float kLowSunDegrees = 3.0f;
constexpr float kOffScreenSunDegrees = 20.0f;
constexpr float kFarCameraHeights[] = {30.0f, 100.0f};
constexpr float kGoldenRatioFraction = 0.618034f;
constexpr float kJitterUlpBelowOne = 5.9604645e-8f;
constexpr int kJitterUlpsBelowOne = 8;
constexpr float kSidewaysLightSteps[] = {0.0f, 0.01f, 0.02f, 0.03f};
constexpr UINT kNoiselessTexel = 0;
constexpr float kDegrees = 3.14159265f / 180.0f;
constexpr int kCompositeConstantRegisters = 100;
constexpr int kCompositeRegister = 96;
constexpr float kDebugRadianceView = 1.0f;
constexpr float kPixelsPerFallbackTexel = 2.0f * kSize;
constexpr float kMaxFallbackDifference = 1.0e-4f;
constexpr float kMaxNoisyMarchDifference = 1.0e-4f;
constexpr float kFiftyDegreeProjectionScale = 2.1445069f;
constexpr float kBlendWallCameraHeight = 30.0f;
constexpr float kBlendWallViewZ = 950.0f;
constexpr float kBlendWallTop = 110.0f;
constexpr float kSunAboveBlendWallDegrees = 10.0f;
constexpr float kMaxFaceRowChange = 0.1f;
constexpr float kMinFaceLoss = 0.05f;
constexpr float kMinMeanLossBelowFaceTop = 0.01f;
constexpr float kRidgeProjectionScale = 8.0f;
constexpr float kRidgeCameraHeight = 100.0f;
constexpr float kDistantRidgeTopDegrees = 3.0f;
constexpr float kSunBehindRidgeDegrees = 2.0f;
constexpr float kRidgeLayerDensity = 0.0015f;
constexpr float kMaxBlendStartChange = 0.1f;
constexpr float kMaxShareBehindRidge = 0.5f;
constexpr float kSkylineCameraHeight = 3.0f;
constexpr float kLowRidgeTopDegrees = 2.0f;
constexpr float kSunBesideTrunkDegrees = 3.0f;
constexpr float kSunBesideTrunkAzimuths[] = {1.5f, 3.0f};
constexpr float kMaxSkylineChange = 0.1f;
constexpr float kThinPostViewZ = 400.0f;
constexpr float kThinPostColumnsFromSun[] = {-200.0f, 200.0f};
constexpr float kThinPostRowMargin = 4.0f;
constexpr float kPostEdgeBeforeColumn = 0.25f;
constexpr float kUntappedColumnPeriod = 4.0f;
constexpr int kFilteredFrames = 2;

struct PixelRect
{
    UINT x0, y0, x1, y1;
};

constexpr PixelRect kCliffFace = {8, 17, 56, 32};
constexpr PixelRect kCliffBelowCharacter = {34, 27, 40, 32};
constexpr PixelRect kTreeGap = {35, 0, 38, kSize - 1};
constexpr PixelRect kBesideTrunk = {14, 18, 22, 30};
constexpr PixelRect kDistantRidgeFace = {8, 21, 56, 31};
constexpr PixelRect kSkyAboveRidge = {33, 12, 40, 18};

struct ViewBox
{
    Vec3 lo;
    Vec3 hi;
};

constexpr ViewBox kCliff = {{-300.0f, -10.0f, 300.0f}, {300.0f, 150.0f, 360.0f}};
constexpr ViewBox kCharacter = {{1.25f, 2.75f, 15.0f}, {3.25f, 4.75f, 16.0f}};
constexpr ViewBox kLeftTrunk = {{-8.0f, -10.0f, 40.0f}, {3.2f, 60.0f, 41.5f}};
constexpr ViewBox kRightTrunk = {{8.8f, -10.0f, 40.0f}, {20.0f, 60.0f, 41.5f}};
constexpr ViewBox kDistantRidge = {{-3000.0f, -10.0f, 2500.0f}, {3000.0f, 1000.0f, 2600.0f}};
constexpr ViewBox kTrunkBelowTheSun = {{-0.5f, -kSkylineCameraHeight, 30.0f}, {0.5f, 9.0f, 31.0f}};

Vec3 PixelRay(UINT x, UINT y)
{
    return {(x + 0.5f) / kSize * 2.0f - 1.0f, 1.0f - (y + 0.5f) / kSize * 2.0f, 1.0f};
}

float BoxHitViewZ(const ViewBox& box, Vec3 ray)
{
    const float direction[3] = {ray.x, ray.y, ray.z};
    const float lo[3] = {box.lo.x, box.lo.y, box.lo.z};
    const float hi[3] = {box.hi.x, box.hi.y, box.hi.z};
    float enter = 0.0f;
    float leave = kNoHit;
    for (int axis = 0; axis < 3; ++axis)
    {
        if (std::fabs(direction[axis]) < kParallelRay)
        {
            if (lo[axis] > 0.0f || hi[axis] < 0.0f)
                return kNoHit;
            continue;
        }
        float slabEnter = lo[axis] / direction[axis];
        float slabLeave = hi[axis] / direction[axis];
        if (slabEnter > slabLeave)
            std::swap(slabEnter, slabLeave);
        enter = std::max(enter, slabEnter);
        leave = std::min(leave, slabLeave);
        if (enter > leave)
            return kNoHit;
    }
    return enter;
}

float RawDepthOfViewZ(float viewZ)
{
    if (viewZ >= kNoHit)
        return kSkyDepth;
    if (viewZ > kFarClip)
        return kDistantTerrainDepth;
    return kDepthAtInfiniteViewZ + kDepthPerInverseViewZ / viewZ;
}

std::vector<float> SceneDepth(std::initializer_list<ViewBox> boxes)
{
    std::vector<float> depth(kSize * kSize);
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const Vec3 ray = PixelRay(x, y);
            float viewZ = ray.y < 0.0f ? kGroundViewY / ray.y : kNoHit;
            for (const ViewBox& box : boxes)
                viewZ = std::min(viewZ, BoxHitViewZ(box, ray));
            depth[y * kSize + x] = RawDepthOfViewZ(viewZ);
        }
    return depth;
}

bool IsSkyDepth(float depth)
{
    return depth >= std::max(kDeepestWorldDepth, kSkyMinDepth);
}

float ViewZOfRawDepth(float depth)
{
    return depth > kDeepestWorldDepth ? kMaxFogDistance : kDepthPerInverseViewZ / (depth - kDepthAtInfiniteViewZ);
}

std::vector<float> FlatGroundDepth(float projectionScale, float cameraHeight)
{
    std::vector<float> depth(kSize * kSize);
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const float rayY = PixelRay(x, y).y / projectionScale;
            depth[y * kSize + x] = RawDepthOfViewZ(rayY < 0.0f ? -cameraHeight / rayY : kNoHit);
        }
    return depth;
}

std::vector<float> WallOverFlatGroundDepth(float projectionScale, float cameraHeight, float wallViewZ, float wallTop)
{
    std::vector<float> depth = FlatGroundDepth(projectionScale, cameraHeight);
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const float heightOnWall = cameraHeight + PixelRay(x, y).y / projectionScale * wallViewZ;
            if (heightOnWall >= 0.0f && heightOnWall <= wallTop)
                depth[y * kSize + x] = RawDepthOfViewZ(wallViewZ);
        }
    return depth;
}

std::vector<float> DistantRidgeOverFlatGroundDepth(float projectionScale, float cameraHeight, float ridgeTopDegrees)
{
    std::vector<float> depth = FlatGroundDepth(projectionScale, cameraHeight);
    const float ridgeTop = std::tan(ridgeTopDegrees * kDegrees);
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
            if (IsSkyDepth(depth[y * kSize + x]) && PixelRay(x, y).y / projectionScale < ridgeTop)
                depth[y * kSize + x] = kDistantTerrainDepth;
    return depth;
}

std::vector<float> WithBox(std::vector<float> depth, float projectionScale, const ViewBox& box)
{
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const Vec3 ray = PixelRay(x, y);
            const Vec3 scaledRay = {ray.x / projectionScale, ray.y / projectionScale, ray.z};
            float& raw = depth[y * kSize + x];
            raw = std::min(raw, RawDepthOfViewZ(BoxHitViewZ(box, scaledRay)));
        }
    return depth;
}

Vec3 SunAt(float elevationDegrees, float azimuthDegrees)
{
    const float elevation = elevationDegrees * kDegrees;
    const float azimuth = azimuthDegrees * kDegrees;
    return {std::sin(azimuth) * std::cos(elevation), std::sin(elevation), std::cos(azimuth) * std::cos(elevation)};
}

FogParams FixtureFog()
{
    FogParams fog = {};
    fog.layers[0].density = kLayerDensity;
    std::copy(std::begin(kLayerDiffuse), std::end(kLayerDiffuse), fog.layers[0].diffuse);
    fog.lightAboveHorizon = 1.0f;
    return fog;
}

LightOnScreen FixtureLightOnScreen(Vec3 toLight, float projectionScale = 1.0f)
{
    const float toLightInView[3] = {toLight.x, toLight.y, toLight.z};
    float projection[16] = {};
    projection[0] = projectionScale;
    projection[5] = projectionScale;
    const D3DVIEWPORT9 viewport = {0, 0, kSize, kSize, 0.0f, 1.0f};
    return ProjectLightOntoViewport(toLightInView, projection, viewport);
}

LightShadowConstants FixtureLightShadow(Vec3 toLight, float haloOcclusion, float projectionScale = 1.0f)
{
    Config config;
    config.haloOcclusion = haloOcclusion;
    return LightShadowFor(FixtureLightOnScreen(toLight, projectionScale), config, FixtureFog());
}

march_layers::Layer FixtureLayer(float diffuseScale, float density)
{
    march_layers::Layer layer = {};
    layer.density = density;
    layer.g = kLayerPhaseG;
    for (int c = 0; c < 3; ++c)
    {
        layer.emissive[c] = kLayerEmissive[c];
        layer.shadowEmissive[c] = kLayerEmissive[c];
        layer.diffuse[c] = kLayerDiffuse[c] * diffuseScale;
    }
    layer.exponent = 1.0f;
    layer.shadowDensity = 1.0f;
    layer.limit = kMaxFogDistance;
    return layer;
}

struct MarchCase
{
    const std::vector<float>* depth;
    Vec3 toLight;
    float haloOcclusion;
    float diffuseScale;
    bool jitter;
    float frame;
    float projectionScale = 1.0f;
    float density = kLayerDensity;
};

void FillConstants(float constants[kConstantRegisters][4], const MarchCase& march)
{
    std::memset(constants, 0, sizeof(float) * kConstantRegisters * 4);
    const float worldViewport[4] = {0.0f, 0.0f, static_cast<float>(kSize), static_cast<float>(kSize)};
    const float pixelGrid[4] = {1.0f, march.frame, 1.0f / kSize, 1.0f / kSize};
    const float viewToNdc[4] = {march.projectionScale, march.projectionScale, 0.0f, 0.0f};
    const float depthToViewZ[4] = {kDepthAtInfiniteViewZ, kDepthPerInverseViewZ, kMaxFogDistance, kDeepestWorldDepth};
    const float viewToWorld[4][4] = {{0, -1, 0, 0}, {0, 0, 1, 0}, {1, 0, 0, 0}, {100, -50, 20, 1}};
    const float lowResTarget[4] = {static_cast<float>(kSize), static_cast<float>(kSize), 1.0f / kSize, 1.0f / kSize};
    const float light[4] = {march.toLight.x, march.toLight.y, march.toLight.z, 1.0f};
    const LightShadowConstants shadow =
        FixtureLightShadow(march.toLight, march.haloOcclusion, march.projectionScale);
    const float marchControl[4] = {march.jitter ? 1.0f : 0.0f, kDistanceCurveRange, kHorizonBlendStart, kFarClip};
    const march_layers::Layer layer = FixtureLayer(march.diffuseScale, march.density);
    std::memcpy(constants[0], worldViewport, sizeof(worldViewport));
    std::memcpy(constants[1], pixelGrid, sizeof(pixelGrid));
    std::memcpy(constants[2], viewToNdc, sizeof(viewToNdc));
    std::memcpy(constants[3], depthToViewZ, sizeof(depthToViewZ));
    std::memcpy(&constants[4][0], viewToWorld, sizeof(viewToWorld));
    std::memcpy(constants[8], lowResTarget, sizeof(lowResTarget));
    std::memcpy(constants[kLightRegister], light, sizeof(light));
    std::memcpy(constants[kLightShadowRegister], &shadow, sizeof(shadow));
    std::memcpy(constants[kMarchRegister], marchControl, sizeof(marchControl));
    std::memcpy(constants[kFirstLayerRegister], &layer, sizeof(layer));
}

struct Resources
{
    IDirect3DSurface9* target = nullptr;
    IDirect3DSurface9* readback = nullptr;
    IDirect3DTexture9* depth = nullptr;
    IDirect3DVolumeTexture9* noise = nullptr;
    IDirect3DTexture9* emptyLowRes = nullptr;
    IDirect3DSurface9* previousTarget = nullptr;
    IDirect3DSurface9* previousDepth = nullptr;
    IDirect3DStateBlock9* previousState = nullptr;

    ~Resources()
    {
        for (IUnknown* resource : std::initializer_list<IUnknown*>{target, readback, depth, noise, emptyLowRes,
                                                                   previousTarget, previousDepth, previousState})
            if (resource)
                resource->Release();
    }
};

bool CreateEmptyLowResTexture(IDirect3DDevice9* device, IDirect3DTexture9** texture)
{
    D3DLOCKED_RECT locked = {};
    if (FAILED(device->CreateTexture(1, 1, 1, 0, D3DFMT_A32B32G32R32F, D3DPOOL_MANAGED, texture, nullptr)) ||
        FAILED((*texture)->LockRect(0, &locked, nullptr, 0)))
        return false;
    std::memset(locked.pBits, 0, 4 * sizeof(float));
    return SUCCEEDED((*texture)->UnlockRect(0));
}

bool CreateResources(IDirect3DDevice9* device, Resources& resources)
{
    return SUCCEEDED(device->CreateStateBlock(D3DSBT_ALL, &resources.previousState)) &&
           SUCCEEDED(device->GetRenderTarget(0, &resources.previousTarget)) &&
           SUCCEEDED(device->GetDepthStencilSurface(&resources.previousDepth)) &&
           SUCCEEDED(device->CreateRenderTarget(kSize, kSize, D3DFMT_A32B32G32R32F, D3DMULTISAMPLE_NONE, 0, FALSE,
                                                &resources.target, nullptr)) &&
           SUCCEEDED(device->CreateOffscreenPlainSurface(kSize, kSize, D3DFMT_A32B32G32R32F, D3DPOOL_SYSTEMMEM,
                                                         &resources.readback, nullptr)) &&
           SUCCEEDED(device->CreateTexture(kSize, kSize, 1, 0, D3DFMT_R32F, D3DPOOL_MANAGED, &resources.depth,
                                           nullptr)) &&
           CreateDensityNoise(device, &resources.noise) &&
           CreateEmptyLowResTexture(device, &resources.emptyLowRes);
}

void BindResources(IDirect3DDevice9* device, const Resources& resources)
{
    const D3DVIEWPORT9 viewport = {0, 0, kSize, kSize, 0.0f, 1.0f};
    device->SetDepthStencilSurface(nullptr);
    device->SetRenderTarget(0, resources.target);
    device->SetViewport(&viewport);
    device->SetVertexShader(nullptr);
    device->SetFVF(D3DFVF_XYZRHW);
    device->SetTexture(0, resources.depth);
    device->SetTexture(1, resources.emptyLowRes);
    device->SetTexture(4, resources.emptyLowRes);
    device->SetTexture(8, nullptr);
    device->SetTexture(9, resources.noise);
    for (DWORD stage : {0u, 1u, 4u, 9u})
    {
        const D3DTEXTUREFILTERTYPE filter = stage == 9 ? D3DTEXF_LINEAR : D3DTEXF_POINT;
        const D3DTEXTUREADDRESS address = stage == 9 ? D3DTADDRESS_WRAP : D3DTADDRESS_CLAMP;
        device->SetSamplerState(stage, D3DSAMP_MINFILTER, filter);
        device->SetSamplerState(stage, D3DSAMP_MAGFILTER, filter);
        device->SetSamplerState(stage, D3DSAMP_MIPFILTER, D3DTEXF_NONE);
        device->SetSamplerState(stage, D3DSAMP_SRGBTEXTURE, FALSE);
        device->SetSamplerState(stage, D3DSAMP_ADDRESSU, address);
        device->SetSamplerState(stage, D3DSAMP_ADDRESSV, address);
        device->SetSamplerState(stage, D3DSAMP_ADDRESSW, address);
    }
    device->SetRenderState(D3DRS_ZENABLE, D3DZB_FALSE);
    device->SetRenderState(D3DRS_ZWRITEENABLE, FALSE);
    device->SetRenderState(D3DRS_ALPHABLENDENABLE, FALSE);
    device->SetRenderState(D3DRS_ALPHATESTENABLE, FALSE);
    device->SetRenderState(D3DRS_STENCILENABLE, FALSE);
    device->SetRenderState(D3DRS_SCISSORTESTENABLE, FALSE);
    device->SetRenderState(D3DRS_FOGENABLE, FALSE);
    device->SetRenderState(D3DRS_CULLMODE, D3DCULL_NONE);
    device->SetRenderState(D3DRS_COLORWRITEENABLE, 0xF);
    device->SetRenderState(D3DRS_SRGBWRITEENABLE, FALSE);
}

bool UploadDepth(IDirect3DTexture9* texture, const std::vector<float>& depth)
{
    D3DLOCKED_RECT locked = {};
    if (FAILED(texture->LockRect(0, &locked, nullptr, 0)))
        return false;
    for (UINT y = 0; y < kSize; ++y)
        std::memcpy(static_cast<BYTE*>(locked.pBits) + y * locked.Pitch, &depth[y * kSize], kSize * sizeof(float));
    return SUCCEEDED(texture->UnlockRect(0));
}

bool RenderPass(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                const std::vector<float>& depth, const float* constants, UINT registers, std::vector<float>& pixels)
{
    const float quad[4][4] = {{-0.5f, -0.5f, 0, 1}, {kSize - 0.5f, -0.5f, 0, 1},
                             {-0.5f, kSize - 0.5f, 0, 1}, {kSize - 0.5f, kSize - 0.5f, 0, 1}};
    if (!UploadDepth(resources.depth, depth))
        return false;
    device->SetPixelShader(shader);
    device->SetPixelShaderConstantF(0, constants, registers);
    if (FAILED(device->BeginScene()))
        return false;
    const HRESULT draw = device->DrawPrimitiveUP(D3DPT_TRIANGLESTRIP, 2, quad, sizeof(quad[0]));
    device->EndScene();
    D3DLOCKED_RECT locked = {};
    if (FAILED(draw) || FAILED(device->GetRenderTargetData(resources.target, resources.readback)) ||
        FAILED(resources.readback->LockRect(&locked, nullptr, D3DLOCK_READONLY)))
        return false;
    pixels.assign(kSize * kSize * 4, 0.0f);
    for (UINT y = 0; y < kSize; ++y)
        std::memcpy(&pixels[y * kSize * 4], static_cast<const BYTE*>(locked.pBits) + y * locked.Pitch,
                    kSize * 4 * sizeof(float));
    return SUCCEEDED(resources.readback->UnlockRect());
}

bool RenderMarch(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                 const MarchCase& march, std::vector<float>& pixels)
{
    float constants[kConstantRegisters][4];
    FillConstants(constants, march);
    return RenderPass(device, resources, shader, *march.depth, &constants[0][0], kConstantRegisters, pixels);
}

bool RenderCompositeFallback(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                             const MarchCase& march, std::vector<float>& pixels)
{
    float constants[kCompositeConstantRegisters][4] = {};
    FillConstants(constants, march);
    constants[1][0] = kPixelsPerFallbackTexel;
    const float lowResTarget[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    const float composite[4] = {1.0f, 0.0f, kDebugRadianceView, 0.0f};
    std::memcpy(constants[8], lowResTarget, sizeof(lowResTarget));
    std::memcpy(constants[kCompositeRegister], composite, sizeof(composite));
    return RenderPass(device, resources, shader, *march.depth, &constants[0][0], kCompositeConstantRegisters,
                      pixels);
}

struct ShadowedMarch
{
    std::vector<float> shadowed;
    std::vector<float> unshadowed;
    std::vector<float> ambient;
};

using PassRenderer = bool (*)(IDirect3DDevice9*, const Resources&, IDirect3DPixelShader9*, const MarchCase&,
                              std::vector<float>&);

bool RenderWithAndWithoutShadow(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                                PassRenderer render, const MarchCase& shadowed, ShadowedMarch& out)
{
    MarchCase unshadowed = shadowed;
    unshadowed.haloOcclusion = 0.0f;
    MarchCase ambient = unshadowed;
    ambient.diffuseScale = 0.0f;
    return render(device, resources, shader, shadowed, out.shadowed) &&
           render(device, resources, shader, unshadowed, out.unshadowed) &&
           render(device, resources, shader, ambient, out.ambient);
}

bool MarchWithAndWithoutShadow(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                               const std::vector<float>& depth, ShadowedMarch& out)
{
    return RenderWithAndWithoutShadow(device, resources, shader, RenderMarch,
                                      {&depth, Norm(kToLightAhead), 1.0f, 1.0f, false, 0.0f}, out);
}

float DirectShare(const ShadowedMarch& march, UINT x, UINT y)
{
    const size_t red = (static_cast<size_t>(y) * kSize + x) * 4;
    const float unshadowed = march.unshadowed[red] - march.ambient[red];
    return (march.shadowed[red] - march.ambient[red]) / std::max(unshadowed, kMinDirectRadiance);
}

struct ShareRange
{
    float lowest = std::numeric_limits<float>::max();
    float highest = std::numeric_limits<float>::lowest();
};

ShareRange DirectShareIn(const ShadowedMarch& march, const PixelRect& rect)
{
    ShareRange range;
    for (UINT y = rect.y0; y <= rect.y1; ++y)
        for (UINT x = rect.x0; x <= rect.x1; ++x)
        {
            const float share = DirectShare(march, x, y);
            range.lowest = std::min(range.lowest, share);
            range.highest = std::max(range.highest, share);
        }
    return range;
}

float LargestRelativeDifference(const std::vector<float>& a, const std::vector<float>& b)
{
    float worst = 0.0f;
    for (size_t i = 0; i < a.size() && i < b.size(); ++i)
        worst = std::max(worst, std::fabs(a[i] - b[i]) / std::max(1.0f, std::fabs(b[i])));
    return a.size() == b.size() ? worst : std::numeric_limits<float>::max();
}

float LargestOpacityChange(const std::vector<float>& a, const std::vector<float>& b)
{
    float worst = 0.0f;
    for (size_t i = 3; i < a.size() && i < b.size(); i += 4)
        worst = std::max(worst, std::fabs(a[i] - b[i]));
    return worst;
}

struct GroundLoss
{
    float skyChange = 0.0f;
    float worstGround = 0.0f;
    float meanGround = 0.0f;
};

GroundLoss FlatGroundLoss(const ShadowedMarch& march, const std::vector<float>& depth)
{
    GroundLoss loss;
    int groundPixels = 0;
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const float raw = depth[y * kSize + x];
            const float lost = 1.0f - DirectShare(march, x, y);
            if (IsSkyDepth(raw))
            {
                const size_t red = (static_cast<size_t>(y) * kSize + x) * 4;
                loss.skyChange = std::max(loss.skyChange, std::fabs(march.shadowed[red] - march.unshadowed[red]) /
                                                              std::max(1.0f, march.unshadowed[red]));
                continue;
            }
            if (ViewZOfRawDepth(raw) >= kHorizonBlendStart)
                continue;
            loss.worstGround = std::max(loss.worstGround, std::fabs(lost));
            loss.meanGround += lost;
            ++groundPixels;
        }
    loss.meanGround /= std::max(groundPixels, 1);
    return loss;
}

void CheckShadowsOfOneQuality(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                              int quality)
{
    const std::vector<float> cliff = SceneDepth({kCliff});
    const std::vector<float> character = SceneDepth({kCliff, kCharacter});
    const std::vector<float> trees = SceneDepth({kLeftTrunk, kRightTrunk});
    const std::vector<float> ground = SceneDepth({});
    const std::vector<float> ridge = SceneDepth({kDistantRidge});
    ShadowedMarch cliffMarch, characterMarch, treeMarch, groundMarch, ridgeMarch;
    std::vector<float> ambientShadowed;
    const Vec3 toLight = Norm(kToLightAhead);
    const bool rendered =
        MarchWithAndWithoutShadow(device, resources, shader, cliff, cliffMarch) &&
        MarchWithAndWithoutShadow(device, resources, shader, character, characterMarch) &&
        MarchWithAndWithoutShadow(device, resources, shader, trees, treeMarch) &&
        MarchWithAndWithoutShadow(device, resources, shader, ground, groundMarch) &&
        MarchWithAndWithoutShadow(device, resources, shader, ridge, ridgeMarch) &&
        RenderMarch(device, resources, shader, {&cliff, toLight, 1.0f, 0.0f, false, 0.0f}, ambientShadowed);

    const ShareRange cliffShare = DirectShareIn(cliffMarch, kCliffFace);
    const float opacityChange = LargestOpacityChange(cliffMarch.shadowed, cliffMarch.unshadowed);
    const float ambientChange = LargestRelativeDifference(ambientShadowed, cliffMarch.ambient);
    char label[320];
    std::snprintf(label, sizeof(label),
                  "quality %d: a cliff that hides the light shadows the direct light in the fog in front of it (at "
                  "most %.3f of it left) and leaves the opacity (%.2g) and the emissive light (%.2g) alone",
                  quality, cliffShare.highest, opacityChange, ambientChange);
    Check(rendered && cliffShare.highest <= kMaxDirectShareBehindSolid && opacityChange <= kMaxOpacityChange &&
              ambientChange <= kMaxOpacityChange,
          label);

    const ShareRange characterShare = DirectShareIn(characterMarch, kCliffBelowCharacter);
    std::snprintf(label, sizeof(label),
                  "quality %d: a character in front of the light keeps the cliff's shadow behind it (at most %.3f of "
                  "the direct light left below it)",
                  quality, characterShare.highest);
    Check(rendered && characterShare.highest <= kMaxDirectShareBehindSolid, label);

    const ShareRange gapShare = DirectShareIn(treeMarch, kTreeGap);
    const ShareRange besideShare = DirectShareIn(treeMarch, kBesideTrunk);
    const float gapLoss = std::max(std::fabs(1.0f - gapShare.lowest), std::fabs(1.0f - gapShare.highest));
    std::snprintf(label, sizeof(label),
                  "quality %d: the fog seen through a gap between two trunks keeps the direct light (%.3g lost), "
                  "while the sky beside a trunk loses %.3f to %.3f of it behind the trunk's assumed thickness",
                  quality, gapLoss, 1.0f - besideShare.highest, 1.0f - besideShare.lowest);
    Check(rendered && gapLoss <= kMaxGapLoss && 1.0f - besideShare.highest >= kMinLossBesideTrunk &&
              1.0f - besideShare.lowest <= kMaxLossBesideTrunk,
          label);

    const GroundLoss groundLoss = FlatGroundLoss(groundMarch, ground);
    std::snprintf(label, sizeof(label),
                  "quality %d: flat ground does not shadow the fog in front of itself (sky %.2g, ground at most %.4f "
                  "and %.5f on average, the depth texels' quantisation)",
                  quality, groundLoss.skyChange, groundLoss.worstGround, groundLoss.meanGround);
    Check(rendered && groundLoss.skyChange <= kMaxUnshadowedChange && groundLoss.worstGround <= kMaxGroundLoss &&
              groundLoss.meanGround <= kMaxMeanGroundLoss,
          label);

    const ShareRange ridgeShare = DirectShareIn(ridgeMarch, kDistantRidgeFace);
    const ShareRange skyShare = DirectShareIn(ridgeMarch, kSkyAboveRidge);
    std::snprintf(label, sizeof(label),
                  "quality %d: distant terrain beyond the far clip that hides the light shadows the sky above it (at "
                  "most %.3f of the direct light left), while its own fog, whose depth there is unknown, keeps the "
                  "direct light (%.2g lost)",
                  quality, skyShare.highest, 1.0f - ridgeShare.lowest);
    Check(rendered && skyShare.highest <= 1.0f - kMinSkyLossAboveRidge &&
              1.0f - ridgeShare.lowest <= kMaxUnshadowedLoss,
          label);
}

void CheckJitterNextToOneOfOneQuality(IDirect3DDevice9* device, const Resources& resources,
                                      IDirect3DPixelShader9* shader, int quality)
{
    const std::vector<float> ground = SceneDepth({});
    const size_t red = (static_cast<size_t>(kNoiselessTexel) * kSize + kNoiselessTexel) * 4;
    float largestChange = 0.0f;
    bool rendered = true;
    for (float sideways : kSidewaysLightSteps)
        for (int ulps = 1; ulps <= kJitterUlpsBelowOne; ++ulps)
        {
            const float frame = (1.0f - ulps * kJitterUlpBelowOne) / kGoldenRatioFraction;
            const Vec3 toLight = Norm({kToLightAhead.x + sideways, kToLightAhead.y, kToLightAhead.z});
            std::vector<float> shadowed, unshadowed;
            rendered = RenderMarch(device, resources, shader, {&ground, toLight, 1.0f, 1.0f, true, frame}, shadowed) &&
                       RenderMarch(device, resources, shader, {&ground, toLight, 0.0f, 1.0f, true, frame},
                                   unshadowed) &&
                       rendered;
            for (size_t c = 0; c < 3 && rendered; ++c)
                largestChange = std::max(largestChange, std::fabs(shadowed[red + c] - unshadowed[red + c]) /
                                                            std::max(1.0f, unshadowed[red + c]));
        }
    char label[256];
    std::snprintf(label, sizeof(label),
                  "quality %d: a step jitter a few ulps below 1 leaves a sky ray with only sky on its segment lit "
                  "(%.2g changed)",
                  quality, largestChange);
    Check(rendered && largestChange <= kMaxUnshadowedChange, label);
}

void CheckStrengthLightAndRepeatability(IDirect3DDevice9* device, const Resources& resources,
                                        IDirect3DPixelShader9* unrolled, IDirect3DPixelShader9* looped)
{
    const std::vector<float> character = SceneDepth({kCliff, kCharacter});
    const Vec3 ahead = Norm(kToLightAhead);
    const Vec3 behind = Norm(kToLightBehind);
    std::vector<float> full, half, none, behindShadowed, behindUnshadowed, jittered[2], loopedJittered;
    const bool rendered =
        RenderMarch(device, resources, unrolled, {&character, ahead, 1.0f, 1.0f, false, 0.0f}, full) &&
        RenderMarch(device, resources, unrolled, {&character, ahead, kHalfStrength, 1.0f, false, 0.0f}, half) &&
        RenderMarch(device, resources, unrolled, {&character, ahead, 0.0f, 1.0f, false, 0.0f}, none) &&
        RenderMarch(device, resources, unrolled, {&character, behind, 1.0f, 1.0f, false, 0.0f}, behindShadowed) &&
        RenderMarch(device, resources, unrolled, {&character, behind, 0.0f, 1.0f, false, 0.0f}, behindUnshadowed) &&
        RenderMarch(device, resources, unrolled, {&character, ahead, 1.0f, 1.0f, true, kJitterFrame}, jittered[0]) &&
        RenderMarch(device, resources, unrolled, {&character, ahead, 1.0f, 1.0f, true, kJitterFrame}, jittered[1]) &&
        RenderMarch(device, resources, looped, {&character, ahead, 1.0f, 1.0f, true, kLoopedJitterFrame},
                    loopedJittered);

    std::vector<float> midway(full.size());
    for (size_t i = 0; i < full.size() && i < none.size(); ++i)
        midway[i] = (full[i] + none[i]) * 0.5f;
    const float linearity = LargestRelativeDifference(half, midway);
    char label[256];
    std::snprintf(label, sizeof(label),
                  "HaloOcclusion=0.5 takes half of the shadowed direct light (%.2g from the midway march)", linearity);
    Check(rendered && linearity <= kMaxLinearityError, label);

    const bool behindUnchanged = rendered && behindShadowed == behindUnshadowed;
    Check(behindUnchanged && FixtureLightShadow(behind, 1.0f).strength == 0.0f,
          "a light behind the camera uploads no shadow and leaves the march unchanged");

    Check(rendered && jittered[0] == jittered[1], "the jittered march with the shadow repeats bit for bit");

    std::vector<float> unrolledJittered;
    const bool unrolledRendered =
        RenderMarch(device, resources, unrolled, {&character, ahead, 1.0f, 1.0f, true, kLoopedJitterFrame},
                    unrolledJittered);
    const float loopedDifference = LargestRelativeDifference(loopedJittered, unrolledJittered);
    std::snprintf(label, sizeof(label),
                  "the per-layer loop of the lit march shadows the direct light as the unrolled march does (%.2g)",
                  loopedDifference);
    Check(rendered && unrolledRendered && loopedDifference <= kMaxLoopedDifference, label);
}

void CheckHaloOcclusionMarch(IDirect3DDevice9* device)
{
    Resources resources;
    const bool ready = CreateResources(device, resources);
    Check(ready, "halo occlusion march targets, depth and density noise created");
    if (!ready)
        return;
    BindResources(device, resources);
    const BYTE* const marches[3] = {g_ps_march_low, g_ps_march_mid, g_ps_march_high};
    for (int quality = 0; quality < 3; ++quality)
    {
        IDirect3DPixelShader9* shader = nullptr;
        const bool created = SUCCEEDED(device->CreatePixelShader(reinterpret_cast<const DWORD*>(marches[quality]),
                                                                 &shader));
        Check(created, "halo occlusion march shader created");
        if (created)
        {
            CheckShadowsOfOneQuality(device, resources, shader, quality + 1);
            CheckJitterNextToOneOfOneQuality(device, resources, shader, quality + 1);
        }
        if (shader)
            shader->Release();
    }
    IDirect3DPixelShader9* unrolled = nullptr;
    IDirect3DPixelShader9* looped = nullptr;
    const bool created =
        SUCCEEDED(device->CreatePixelShader(reinterpret_cast<const DWORD*>(g_ps_march_mid), &unrolled)) &&
        SUCCEEDED(device->CreatePixelShader(reinterpret_cast<const DWORD*>(g_ps_lit_march_mid), &looped));
    Check(created, "halo occlusion comparison shaders created");
    if (created)
        CheckStrengthLightAndRepeatability(device, resources, unrolled, looped);
    for (IDirect3DPixelShader9* shader : {unrolled, looped})
        if (shader)
            shader->Release();
    device->SetRenderTarget(0, resources.previousTarget);
    device->SetDepthStencilSurface(resources.previousDepth);
    resources.previousState->Apply();
}

struct FarGroundLoss
{
    float belowBlend = 0.0f;
    float inBlend = 0.0f;
    float distantTerrain = 0.0f;
    float skyChange = 0.0f;
};

FarGroundLoss LossNearTheFarClip(const ShadowedMarch& march, const std::vector<float>& depth)
{
    FarGroundLoss loss;
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const float raw = depth[y * kSize + x];
            const size_t red = (static_cast<size_t>(y) * kSize + x) * 4;
            const float lost = std::fabs(1.0f - DirectShare(march, x, y));
            if (IsSkyDepth(raw))
                loss.skyChange = std::max(loss.skyChange, std::fabs(march.shadowed[red] - march.unshadowed[red]) /
                                                              std::max(1.0f, march.unshadowed[red]));
            else if (raw > kDeepestWorldDepth)
                loss.distantTerrain = std::max(loss.distantTerrain, lost);
            else if (ViewZOfRawDepth(raw) > kHorizonBlendStart)
                loss.inBlend = std::max(loss.inBlend, lost);
            else
                loss.belowBlend = std::max(loss.belowBlend, lost);
        }
    return loss;
}

void CheckFarGroundOfOneQuality(IDirect3DDevice9* device, const Resources& resources, IDirect3DPixelShader9* shader,
                                int quality)
{
    FarGroundLoss worst;
    bool rendered = true;
    for (float cameraHeight : kFarCameraHeights)
    {
        const std::vector<float> ground = FlatGroundDepth(kFarProjectionScale, cameraHeight);
        for (float azimuth : {0.0f, kOffScreenSunDegrees})
        {
            ShadowedMarch march;
            const MarchCase lowSun = {&ground, SunAt(kLowSunDegrees, azimuth), 1.0f, 1.0f, false, 0.0f,
                                      kFarProjectionScale, kThinLayerDensity};
            rendered = RenderWithAndWithoutShadow(device, resources, shader, RenderMarch, lowSun, march) && rendered;
            const FarGroundLoss loss = LossNearTheFarClip(march, ground);
            std::printf("     camera %.0f yd, sun %.0f deg up at azimuth %.0f: direct light lost at most %.4f below "
                        "the horizon blend, %.4f in it, %.4f on distant terrain, sky %.2g\n",
                        cameraHeight, kLowSunDegrees, azimuth, loss.belowBlend, loss.inBlend, loss.distantTerrain,
                        loss.skyChange);
            worst.belowBlend = std::max(worst.belowBlend, loss.belowBlend);
            worst.inBlend = std::max(worst.inBlend, loss.inBlend);
            worst.distantTerrain = std::max(worst.distantTerrain, loss.distantTerrain);
            worst.skyChange = std::max(worst.skyChange, loss.skyChange);
        }
    }
    char label[320];
    std::snprintf(label, sizeof(label),
                  "quality %d: flat ground up to and beyond the far clip keeps the direct light in thin fog under a "
                  "low sun (lost at most %.4f below the horizon blend, %.4f in it, %.4f on distant terrain, sky "
                  "%.2g)",
                  quality, worst.belowBlend, worst.inBlend, worst.distantTerrain, worst.skyChange);
    Check(rendered && worst.belowBlend <= kMaxGroundLoss && worst.inBlend <= kMaxGroundLoss &&
              worst.distantTerrain <= kMaxGroundLoss && worst.skyChange <= kMaxUnshadowedChange,
          label);
}

struct FaceShadow
{
    float largestRowChange = 0.0f;
    float mostLost = 0.0f;
    float meanLostBelowTop = 0.0f;
};

bool OnFace(const std::vector<float>& depth, float faceDepth, UINT x, UINT y, UINT rowsUp)
{
    return y >= rowsUp && depth[(y - rowsUp) * kSize + x] == faceDepth;
}

FaceShadow ShadowDownTheFace(const ShadowedMarch& march, const std::vector<float>& depth, float faceDepth)
{
    FaceShadow face;
    int pixelsBelowTop = 0;
    for (UINT x = 0; x < kSize; ++x)
        for (UINT y = 0; y < kSize; ++y)
        {
            if (!OnFace(depth, faceDepth, x, y, 0))
                continue;
            const float share = DirectShare(march, x, y);
            face.mostLost = std::max(face.mostLost, 1.0f - share);
            if (!OnFace(depth, faceDepth, x, y, 1))
                continue;
            face.largestRowChange = std::max(face.largestRowChange, std::fabs(share - DirectShare(march, x, y - 1)));
            if (OnFace(depth, faceDepth, x, y, 2))
                continue;
            face.meanLostBelowTop += 1.0f - share;
            ++pixelsBelowTop;
        }
    face.meanLostBelowTop /= std::max(pixelsBelowTop, 1);
    return face;
}

struct RidgeShadow
{
    float blendStartChange = 0.0f;
    float groundBeforeBlend = 0.0f;
    float skyAboveRidge = 0.0f;
    float ridgeLoss = 0.0f;
};

bool InHorizonBlendGround(float depth)
{
    return depth <= kDeepestWorldDepth && ViewZOfRawDepth(depth) > kHorizonBlendStart;
}

RidgeShadow ShadowBehindTheRidge(const ShadowedMarch& march, const std::vector<float>& depth)
{
    RidgeShadow ridge;
    for (UINT x = 0; x < kSize; ++x)
        for (UINT y = 1; y < kSize; ++y)
        {
            const float own = depth[y * kSize + x];
            const float above = depth[(y - 1) * kSize + x];
            const float share = DirectShare(march, x, y);
            if (own > kDeepestWorldDepth && !IsSkyDepth(own))
            {
                ridge.ridgeLoss = std::max(ridge.ridgeLoss, std::fabs(1.0f - share));
                if (IsSkyDepth(above))
                    ridge.skyAboveRidge = std::max(ridge.skyAboveRidge, DirectShare(march, x, y - 1));
            }
            if (own > kDeepestWorldDepth || InHorizonBlendGround(own))
                continue;
            ridge.groundBeforeBlend = std::max(ridge.groundBeforeBlend, share);
            if (InHorizonBlendGround(above))
                ridge.blendStartChange =
                    std::max(ridge.blendStartChange, std::fabs(share - DirectShare(march, x, y - 1)));
        }
    return ridge;
}

void CheckOccludersInTheBlendOfOneQuality(IDirect3DDevice9* device, const Resources& resources,
                                          IDirect3DPixelShader9* shader, int quality)
{
    const std::vector<float> wall = WallOverFlatGroundDepth(kFiftyDegreeProjectionScale, kBlendWallCameraHeight,
                                                            kBlendWallViewZ, kBlendWallTop);
    const float wallTopDegrees = std::atan((kBlendWallTop - kBlendWallCameraHeight) / kBlendWallViewZ) / kDegrees;
    const MarchCase sunAboveWall = {&wall, SunAt(wallTopDegrees + kSunAboveBlendWallDegrees, 0.0f), 1.0f, 1.0f,
                                    false, 0.0f, kFiftyDegreeProjectionScale, kThinLayerDensity};
    const std::vector<float> ridge =
        DistantRidgeOverFlatGroundDepth(kRidgeProjectionScale, kRidgeCameraHeight, kDistantRidgeTopDegrees);
    const MarchCase sunBehindRidge = {&ridge, SunAt(kSunBehindRidgeDegrees, 0.0f), 1.0f, 1.0f, false, 0.0f,
                                      kRidgeProjectionScale, kRidgeLayerDensity};
    ShadowedMarch wallMarch, ridgeMarch;
    const bool rendered =
        RenderWithAndWithoutShadow(device, resources, shader, RenderMarch, sunAboveWall, wallMarch) &&
        RenderWithAndWithoutShadow(device, resources, shader, RenderMarch, sunBehindRidge, ridgeMarch);
    const LightOnScreen sun = FixtureLightOnScreen(sunAboveWall.toLight, kFiftyDegreeProjectionScale);

    const FaceShadow face = ShadowDownTheFace(wallMarch, wall, RawDepthOfViewZ(kBlendWallViewZ));
    char label[320];
    std::snprintf(label, sizeof(label),
                  "quality %d: a wall inside the horizon blend with the sun above it on screen shadows its face "
                  "continuously from the row below its top (rows differ by at most %.3f; %.4f of the direct light "
                  "lost on average in that row, up to %.3f)",
                  quality, face.largestRowChange, face.meanLostBelowTop, face.mostLost);
    Check(rendered && sun.inFront && sun.pixel[1] >= 0.0f && face.largestRowChange <= kMaxFaceRowChange &&
              face.meanLostBelowTop >= kMinMeanLossBelowFaceTop && face.mostLost >= kMinFaceLoss,
          label);

    const RidgeShadow behind = ShadowBehindTheRidge(ridgeMarch, ridge);
    std::snprintf(label, sizeof(label),
                  "quality %d: distant terrain hiding the sun shadows the ground's fog continuously across the start "
                  "of the horizon blend (rows differ by %.3f there; at most %.3f of the direct light left before the "
                  "blend and %.3f on the sky above the ridge, %.2g lost in the ridge's own fog)",
                  quality, behind.blendStartChange, behind.groundBeforeBlend, behind.skyAboveRidge, behind.ridgeLoss);
    Check(rendered && behind.blendStartChange <= kMaxBlendStartChange &&
              behind.groundBeforeBlend <= kMaxShareBehindRidge && behind.skyAboveRidge <= kMaxShareBehindRidge &&
              behind.ridgeLoss <= kMaxUnshadowedLoss,
          label);
}

struct SkylineStep
{
    float largest = 0.0f;
    float distantTerrainShare = 1.0f;
    float skyShare = 1.0f;
};

SkylineStep LargestStepAlongTheSkyline(const ShadowedMarch& march, const std::vector<float>& depth)
{
    SkylineStep step;
    for (UINT x = 0; x < kSize; ++x)
        for (UINT y = 1; y < kSize; ++y)
        {
            const float own = depth[y * kSize + x];
            if (own <= kDeepestWorldDepth || IsSkyDepth(own) || !IsSkyDepth(depth[(y - 1) * kSize + x]))
                continue;
            const float share = DirectShare(march, x, y);
            const float skyShare = DirectShare(march, x, y - 1);
            if (std::fabs(share - skyShare) > step.largest)
                step = {std::fabs(share - skyShare), share, skyShare};
        }
    return step;
}

void CheckTrunkBeforeTheSkylineOfOneQuality(IDirect3DDevice9* device, const Resources& resources,
                                            IDirect3DPixelShader9* shader, int quality)
{
    const std::vector<float> skyline = WithBox(
        DistantRidgeOverFlatGroundDepth(kRidgeProjectionScale, kSkylineCameraHeight, kLowRidgeTopDegrees),
        kRidgeProjectionScale, kTrunkBelowTheSun);
    for (float density : {kThinLayerDensity, kRidgeLayerDensity})
    {
        SkylineStep worst;
        bool rendered = true;
        for (float azimuth : kSunBesideTrunkAzimuths)
        {
            ShadowedMarch march;
            const MarchCase sunBesideTrunk = {&skyline, SunAt(kSunBesideTrunkDegrees, azimuth), 1.0f, 1.0f, false,
                                              0.0f, kRidgeProjectionScale, density};
            rendered = RenderWithAndWithoutShadow(device, resources, shader, RenderMarch, sunBesideTrunk, march) &&
                       rendered;
            const SkylineStep step = LargestStepAlongTheSkyline(march, skyline);
            worst = step.largest > worst.largest ? step : worst;
        }
        char label[320];
        std::snprintf(label, sizeof(label),
                      "quality %d, sigma %g/yd: a trunk in front of a distant-terrain skyline beside the sun shadows "
                      "the distant terrain's fog as it does the sky's above it (largest step %.3f: %.3f of the direct "
                      "light left on the distant terrain, %.3f on the sky)",
                      quality, density, worst.largest, worst.distantTerrainShare, worst.skyShare);
        Check(rendered && worst.largest <= kMaxSkylineChange, label);
    }
}

void CheckHaloOcclusionNearTheFarClip(IDirect3DDevice9* device)
{
    Resources resources;
    const bool ready = CreateResources(device, resources);
    Check(ready, "far-clip halo occlusion targets, depth and density noise created");
    if (!ready)
        return;
    BindResources(device, resources);
    const BYTE* const marches[3] = {g_ps_march_low, g_ps_march_mid, g_ps_march_high};
    for (int quality = 0; quality < 3; ++quality)
    {
        IDirect3DPixelShader9* shader = nullptr;
        const bool created = SUCCEEDED(device->CreatePixelShader(reinterpret_cast<const DWORD*>(marches[quality]),
                                                                 &shader));
        Check(created, "far-clip halo occlusion march shader created");
        if (created)
        {
            CheckFarGroundOfOneQuality(device, resources, shader, quality + 1);
            CheckOccludersInTheBlendOfOneQuality(device, resources, shader, quality + 1);
            CheckTrunkBeforeTheSkylineOfOneQuality(device, resources, shader, quality + 1);
        }
        if (shader)
            shader->Release();
    }
    device->SetRenderTarget(0, resources.previousTarget);
    device->SetDepthStencilSurface(resources.previousDepth);
    resources.previousState->Apply();
}

std::vector<float> WithDistantTerrainInTheLastPixel(std::vector<float> depth)
{
    depth.back() = kDistantTerrainDepth;
    return depth;
}

std::vector<bool> FallbackPixels(const std::vector<float>& depth, bool uniformNeighbourhood, bool skyIncluded)
{
    std::vector<bool> compared(depth.size(), false);
    for (UINT y = 0; y < kSize; ++y)
        for (UINT x = 0; x < kSize; ++x)
        {
            const float own = depth[y * kSize + x];
            bool uniform = true;
            for (int dy = -1; dy <= 1; ++dy)
                for (int dx = -1; dx <= 1; ++dx)
                {
                    const int nx = std::clamp(static_cast<int>(x) + dx, 0, static_cast<int>(kSize) - 1);
                    const int ny = std::clamp(static_cast<int>(y) + dy, 0, static_cast<int>(kSize) - 1);
                    uniform = uniform && depth[ny * kSize + nx] == own;
                }
            const bool sky = IsSkyDepth(own);
            const bool distantTerrain = own > kDeepestWorldDepth && !sky;
            compared[y * kSize + x] = !distantTerrain && (uniform || !uniformNeighbourhood) && (skyIncluded || !sky);
        }
    return compared;
}

int ComparedPixels(const std::vector<bool>& compared)
{
    return static_cast<int>(std::count(compared.begin(), compared.end(), true));
}

float LargestRadianceDifference(const std::vector<float>& a, const std::vector<float>& b,
                                const std::vector<bool>& compared)
{
    if (a.size() != b.size() || a.size() != compared.size() * 4)
        return std::numeric_limits<float>::max();
    float worst = 0.0f;
    for (size_t i = 0; i < compared.size(); ++i)
        for (size_t c = 0; c < 3 && compared[i]; ++c)
            worst = std::max(worst, std::fabs(a[i * 4 + c] - b[i * 4 + c]) / std::max(1.0f, std::fabs(b[i * 4 + c])));
    return worst;
}

struct FallbackShaders
{
    IDirect3DPixelShader9* march = nullptr;
    IDirect3DPixelShader9* litMarch = nullptr;
    IDirect3DPixelShader9* noisyMarch = nullptr;
    IDirect3DPixelShader9* composite = nullptr;
    IDirect3DPixelShader9* splitComposite = nullptr;
    IDirect3DPixelShader9* litComposite = nullptr;
    IDirect3DPixelShader9* litSplitComposite = nullptr;
    IDirect3DPixelShader9* noisyComposite = nullptr;
    IDirect3DPixelShader9* noisySplitComposite = nullptr;

    ~FallbackShaders()
    {
        for (IUnknown* shader : std::initializer_list<IUnknown*>{march, litMarch, noisyMarch, composite,
                                                                 splitComposite, litComposite, litSplitComposite,
                                                                 noisyComposite, noisySplitComposite})
            if (shader)
                shader->Release();
    }
};

bool CreateShader(IDirect3DDevice9* device, const BYTE* bytecode, IDirect3DPixelShader9*& shader)
{
    return SUCCEEDED(device->CreatePixelShader(reinterpret_cast<const DWORD*>(bytecode), &shader));
}

bool CreateFallbackShaders(IDirect3DDevice9* device, int quality, FallbackShaders& shaders)
{
    const BYTE* const marches[3] = {g_ps_march_low, g_ps_march_mid, g_ps_march_high};
    const BYTE* const litMarches[3] = {g_ps_lit_march_low, g_ps_lit_march_mid, g_ps_lit_march_high};
    const BYTE* const noisyMarches[3] = {g_ps_noisy_march_low, g_ps_noisy_march_mid, g_ps_noisy_march_high};
    const BYTE* const composites[3] = {g_ps_composite_low, g_ps_composite_mid, g_ps_composite_high};
    const BYTE* const splitComposites[3] = {g_ps_split_composite_low, g_ps_split_composite_mid,
                                            g_ps_split_composite_high};
    const BYTE* const litComposites[3] = {g_ps_lit_composite_low, g_ps_lit_composite_mid, g_ps_lit_composite_high};
    const BYTE* const litSplitComposites[3] = {g_ps_lit_split_composite_low, g_ps_lit_split_composite_mid,
                                               g_ps_lit_split_composite_high};
    const BYTE* const noisyComposites[3] = {g_ps_noisy_composite_low, g_ps_noisy_composite_mid,
                                            g_ps_noisy_composite_high};
    const BYTE* const noisySplitComposites[3] = {g_ps_noisy_split_composite_low, g_ps_noisy_split_composite_mid,
                                                 g_ps_noisy_split_composite_high};
    bool created = CreateShader(device, marches[quality], shaders.march);
    created = CreateShader(device, litMarches[quality], shaders.litMarch) && created;
    created = CreateShader(device, noisyMarches[quality], shaders.noisyMarch) && created;
    created = CreateShader(device, composites[quality], shaders.composite) && created;
    created = CreateShader(device, splitComposites[quality], shaders.splitComposite) && created;
    created = CreateShader(device, litComposites[quality], shaders.litComposite) && created;
    created = CreateShader(device, litSplitComposites[quality], shaders.litSplitComposite) && created;
    created = CreateShader(device, noisyComposites[quality], shaders.noisyComposite) && created;
    return CreateShader(device, noisySplitComposites[quality], shaders.noisySplitComposite) && created;
}

struct FallbackScene
{
    std::vector<float> depth;
    std::vector<bool> allPixels;
    std::vector<bool> uniformPixels;
    std::vector<bool> surfacePixels;
};

FallbackScene FallbackSceneOf(std::initializer_list<ViewBox> boxes)
{
    FallbackScene scene;
    scene.depth = WithDistantTerrainInTheLastPixel(SceneDepth(boxes));
    scene.allPixels = FallbackPixels(scene.depth, false, true);
    scene.uniformPixels = FallbackPixels(scene.depth, true, true);
    scene.surfacePixels = FallbackPixels(scene.depth, false, false);
    return scene;
}

struct FallbackDifferences
{
    float composite = 0.0f;
    float splitComposite = 0.0f;
    float litComposite = 0.0f;
    float litSplitComposite = 0.0f;
    float noisyMarch = 0.0f;
    int pixels = 0;
    int uniformPixels = 0;
};

bool CompareFallbacksInScene(IDirect3DDevice9* device, const Resources& resources, const FallbackShaders& shaders,
                             const FallbackScene& scene, FallbackDifferences& differences)
{
    const MarchCase shadowed = {&scene.depth, Norm(kToLightAhead), 1.0f, 1.0f, false, 0.0f};
    std::vector<float> march, litMarch, noisyMarch, composite, splitComposite, litComposite, litSplitComposite;
    const bool rendered =
        RenderMarch(device, resources, shaders.march, shadowed, march) &&
        RenderMarch(device, resources, shaders.litMarch, shadowed, litMarch) &&
        RenderMarch(device, resources, shaders.noisyMarch, shadowed, noisyMarch) &&
        RenderCompositeFallback(device, resources, shaders.composite, shadowed, composite) &&
        RenderCompositeFallback(device, resources, shaders.splitComposite, shadowed, splitComposite) &&
        RenderCompositeFallback(device, resources, shaders.litComposite, shadowed, litComposite) &&
        RenderCompositeFallback(device, resources, shaders.litSplitComposite, shadowed, litSplitComposite);
    auto worsen = [](float& worst, float difference) { worst = std::max(worst, difference); };
    worsen(differences.composite, LargestRadianceDifference(composite, march, scene.allPixels));
    worsen(differences.splitComposite, LargestRadianceDifference(splitComposite, march, scene.uniformPixels));
    worsen(differences.litComposite, LargestRadianceDifference(litComposite, litMarch, scene.allPixels));
    worsen(differences.litSplitComposite, LargestRadianceDifference(litSplitComposite, litMarch,
                                                                    scene.uniformPixels));
    worsen(differences.noisyMarch, LargestRadianceDifference(noisyMarch, march, scene.allPixels));
    differences.pixels += ComparedPixels(scene.allPixels);
    differences.uniformPixels += ComparedPixels(scene.uniformPixels);
    return rendered;
}

void CheckCompositesOfOneQuality(IDirect3DDevice9* device, const Resources& resources, const FallbackShaders& shaders,
                                 int quality)
{
    const FallbackScene cliff = FallbackSceneOf({kCliff});
    const FallbackScene character = FallbackSceneOf({kCliff, kCharacter});
    const FallbackScene trees = FallbackSceneOf({kLeftTrunk, kRightTrunk});
    const FallbackScene ground = FallbackSceneOf({});
    FallbackDifferences differences;
    bool rendered = true;
    for (const FallbackScene* scene : {&cliff, &character, &trees, &ground})
        rendered = CompareFallbacksInScene(device, resources, shaders, *scene, differences) && rendered;
    char label[400];
    std::snprintf(label, sizeof(label),
                  "quality %d: the composites' full-resolution fallback shadows the direct light as the march does "
                  "at the same pixel (plain %.2g, with local lights %.2g over %d pixels; split %.2g and %.2g over "
                  "%d) on the cliff, the character, the trees and flat ground",
                  quality, differences.composite, differences.litComposite, differences.pixels,
                  differences.splitComposite, differences.litSplitComposite, differences.uniformPixels);
    Check(rendered && differences.composite <= kMaxFallbackDifference &&
              differences.litComposite <= kMaxFallbackDifference &&
              differences.splitComposite <= kMaxFallbackDifference &&
              differences.litSplitComposite <= kMaxFallbackDifference && differences.uniformPixels > 0,
          label);
    std::snprintf(label, sizeof(label),
                  "quality %d: the march with authored noise shadows the direct light as the plain march does (%.2g "
                  "with no noisy layer)",
                  quality, differences.noisyMarch);
    Check(rendered && differences.noisyMarch <= kMaxNoisyMarchDifference, label);

    const MarchCase cliffCase = {&cliff.depth, Norm(kToLightAhead), 1.0f, 1.0f, false, 0.0f};
    const MarchCase characterCase = {&character.depth, Norm(kToLightAhead), 1.0f, 1.0f, false, 0.0f};
    const MarchCase treeCase = {&trees.depth, Norm(kToLightAhead), 1.0f, 1.0f, false, 0.0f};
    std::vector<float> plainCliff, noisyCliff, noisySplitCliff;
    ShadowedMarch plainTrees, noisyTrees, noisySplitTrees, noisyCharacter, noisySplitCharacter;
    const bool noisyRendered =
        RenderCompositeFallback(device, resources, shaders.composite, cliffCase, plainCliff) &&
        RenderCompositeFallback(device, resources, shaders.noisyComposite, cliffCase, noisyCliff) &&
        RenderCompositeFallback(device, resources, shaders.noisySplitComposite, cliffCase, noisySplitCliff) &&
        RenderWithAndWithoutShadow(device, resources, shaders.composite, RenderCompositeFallback, treeCase,
                                   plainTrees) &&
        RenderWithAndWithoutShadow(device, resources, shaders.noisyComposite, RenderCompositeFallback, treeCase,
                                   noisyTrees) &&
        RenderWithAndWithoutShadow(device, resources, shaders.noisySplitComposite, RenderCompositeFallback,
                                   treeCase, noisySplitTrees) &&
        RenderWithAndWithoutShadow(device, resources, shaders.noisyComposite, RenderCompositeFallback,
                                   characterCase, noisyCharacter) &&
        RenderWithAndWithoutShadow(device, resources, shaders.noisySplitComposite, RenderCompositeFallback,
                                   characterCase, noisySplitCharacter);
    std::vector<bool> uniformSurface(cliff.surfacePixels.size());
    for (size_t i = 0; i < uniformSurface.size(); ++i)
        uniformSurface[i] = cliff.surfacePixels[i] && cliff.uniformPixels[i];
    const float solidDifference = std::max(LargestRadianceDifference(noisyCliff, plainCliff, cliff.surfacePixels),
                                           LargestRadianceDifference(noisySplitCliff, plainCliff, uniformSurface));
    const ShareRange characterShare = DirectShareIn(noisyCharacter, kCliffBelowCharacter);
    const ShareRange splitCharacterShare = DirectShareIn(noisySplitCharacter, kCliffBelowCharacter);
    const ShareRange plainBeside = DirectShareIn(plainTrees, kBesideTrunk);
    const ShareRange noisyBeside = DirectShareIn(noisyTrees, kBesideTrunk);
    const ShareRange noisySplitBeside = DirectShareIn(noisySplitTrees, kBesideTrunk);
    const float noisyBesideLoss = std::max(1.0f - std::min(noisyBeside.lowest, noisySplitBeside.lowest),
                                           std::max(noisyBeside.highest, noisySplitBeside.highest) - 1.0f);
    std::snprintf(label, sizeof(label),
                  "quality %d: the noisy composites' fallback, built without thin-caster shadows, matches the plain "
                  "fallback where every caster is solid (%.2g on the cliff and the ground before it), keeps the "
                  "cliff's shadow behind the character (at most %.3f left) and leaves the sky beside a trunk lit "
                  "(%.2g lost, against %.3f to %.3f in the plain fallback)",
                  quality, solidDifference, std::max(characterShare.highest, splitCharacterShare.highest),
                  noisyBesideLoss, 1.0f - plainBeside.highest, 1.0f - plainBeside.lowest);
    Check(noisyRendered && solidDifference <= kMaxFallbackDifference &&
              std::max(characterShare.highest, splitCharacterShare.highest) <= kMaxDirectShareBehindSolid &&
              noisyBesideLoss <= kMaxUnshadowedLoss && 1.0f - plainBeside.highest >= kMinLossBesideTrunk,
          label);
}

void CheckHaloOcclusionInTheComposites(IDirect3DDevice9* device)
{
    Resources resources;
    const bool ready = CreateResources(device, resources);
    Check(ready, "composite halo occlusion targets, depth and density noise created");
    if (!ready)
        return;
    BindResources(device, resources);
    for (int quality = 0; quality < 3; ++quality)
    {
        FallbackShaders shaders;
        const bool created = CreateFallbackShaders(device, quality, shaders);
        Check(created, "composite halo occlusion shaders created");
        if (created)
            CheckCompositesOfOneQuality(device, resources, shaders, quality + 1);
    }
    device->SetRenderTarget(0, resources.previousTarget);
    device->SetDepthStencilSurface(resources.previousDepth);
    resources.previousState->Apply();
}

LightOnScreen UnitLightOnScreen(float viewZ, const float* projection, const D3DVIEWPORT9& viewport)
{
    const float side = std::sqrt(std::max(1.0f - viewZ * viewZ, 0.0f) * 0.5f);
    const float toLightInView[3] = {side, side, viewZ};
    return ProjectLightOntoViewport(toLightInView, projection, viewport);
}

void CheckLightShadowConstants()
{
    const D3DVIEWPORT9 world = {0, 0, 1280, 688, 0.0f, 1.0f};
    const Vec3 eye = Add({0, 0, 9}, kGameLikeWorldOffset);
    const Vec3 at = Add({100, 2, 4}, kGameLikeWorldOffset);
    float view[16];
    float projection[16];
    CameraRelativeLookAt(eye, at, view);
    EngineProjection(1280.0f / 688.0f, projection);
    const FrameInputs input = MakeInputs(view, projection, eye, at, world);
    const Config defaults;
    const FogParams daylight = BuildFogParams(input, defaults, nullptr);

    const D3DVIEWPORT9 offset = {10, 20, 800, 600, 0.0f, 1.0f};
    float offCentre[16];
    std::memcpy(offCentre, projection, sizeof(offCentre));
    offCentre[8] = 0.02f;
    offCentre[9] = -0.03f;
    const Vec3 toLight = Norm({0.2f, 0.3f, 0.9f});
    const float toLightInView[3] = {toLight.x, toLight.y, toLight.z};
    const LightOnScreen onScreen = ProjectLightOntoViewport(toLightInView, offCentre, offset);
    const float ndcX = toLight.x / toLight.z * offCentre[0] + offCentre[8];
    const float ndcY = toLight.y / toLight.z * offCentre[5] + offCentre[9];
    const float column = offset.X + (ndcX * 0.5f + 0.5f) * offset.Width;
    const float row = offset.Y + (0.5f - ndcY * 0.5f) * offset.Height;
    Check(onScreen.inFront && std::fabs(onScreen.pixel[0] - column) <= kMaxConstantError &&
              std::fabs(onScreen.pixel[1] - row) <= kMaxConstantError &&
              std::fabs(onScreen.ndc[0] - ndcX) <= kMaxConstantError &&
              std::fabs(onScreen.ndc[1] - ndcY) <= kMaxConstantError,
          "the light projects onto the viewport where the god rays and the sun marker put it");

    Config full = defaults;
    full.haloOcclusion = 1.0f;
    Config half = defaults;
    Config off = defaults;
    half.haloOcclusion = kHalfStrength;
    off.haloOcclusion = 0.0f;
    const LightShadowConstants fullShadow = LightShadowFor(onScreen, full, daylight);
    Check(FogScattersDirectLight(daylight) && fullShadow.strength == 1.0f &&
              LightShadowFor(onScreen, half, daylight).strength == kHalfStrength &&
              LightShadowFor(onScreen, off, daylight).strength == 0.0f &&
              fullShadow.lightPixel[0] == onScreen.pixel[0] && fullShadow.lightPixel[1] == onScreen.pixel[1] &&
              fullShadow.occluderThicknessShare == kOccluderThicknessShare,
          "the shadow constant carries the light pixel, HaloOcclusion as its strength and the thickness share");

    bool rising = true;
    float previous = -1.0f;
    for (int i = 0; i <= kRampSamples; ++i)
    {
        const float viewZ = kLightInFrontViewZ + (kLightShadowFullViewZ - kLightInFrontViewZ) * i / kRampSamples;
        const float strength = LightShadowStrength(1.0f, viewZ, daylight);
        rising = rising && strength >= previous;
        previous = strength;
    }
    const float atMid = LightShadowStrength(1.0f, kRampMidViewZ, daylight);
    const float atEnd = LightShadowStrength(1.0f, kLightShadowFullViewZ, daylight);
    const float atStart = LightShadowStrength(1.0f, kLightInFrontViewZ, daylight);
    const LightOnScreen nearlySideways = UnitLightOnScreen(kBelowFrontViewZ, projection, world);
    const LightOnScreen behind = UnitLightOnScreen(-0.5f, projection, world);
    std::printf("     halo occlusion strength %.3f at light view z %.3f, %.3f at %.3f\n", atMid, kRampMidViewZ, atEnd,
                kLightShadowFullViewZ);
    Check(rising && std::fabs(atMid - 0.5f) <= kMaxConstantError && atEnd == 1.0f && atStart == 0.0f &&
              !nearlySideways.inFront && LightShadowFor(nearlySideways, full, daylight).strength == 0.0f &&
              !behind.inFront && LightShadowFor(behind, full, daylight).strength == 0.0f,
          "the shadow fades in with the light's view z from 0.05 to 0.2 and is off while the light is behind");

    const auto lightAtNdc = [](float x, float y) {
        LightOnScreen light = {};
        light.inFront = true;
        light.viewZ = kLightInPictureViewZ;
        light.ndc[0] = x;
        light.ndc[1] = y;
        return light;
    };
    bool falling = true;
    float before = 2.0f;
    for (int i = 0; i <= kRampSamples; ++i)
    {
        const float beyondEdge = 1.0f + kLightShadowFadeBeyondPicture * i / kRampSamples;
        const float strength = LightShadowFor(lightAtNdc(0.0f, beyondEdge), full, daylight).strength;
        falling = falling && strength <= before;
        before = strength;
    }
    const float inPicture = LightShadowFor(lightAtNdc(0.6f, -0.9f), full, daylight).strength;
    const float halfWayOut =
        LightShadowFor(lightAtNdc(0.0f, 1.0f + 0.5f * kLightShadowFadeBeyondPicture), full, daylight).strength;
    const float out = LightShadowFor(lightAtNdc(0.0f, 1.0f + kLightShadowFadeBeyondPicture), full, daylight).strength;
    const float aside = LightShadowFor(lightAtNdc(-1.5f, 0.2f), full, daylight).strength;
    std::printf("     halo occlusion strength %.3f in the picture, %.3f half way out, %.3f out, %.3f aside\n",
                inPicture, halfWayOut, out, aside);
    Check(falling && inPicture == 1.0f && std::fabs(halfWayOut - 0.5f) <= kMaxConstantError && out == 0.0f &&
              aside == 0.0f,
          "the shadow fades out while the light leaves the picture, as the occluders beyond its edge are unknown");

    Config sunless = defaults;
    sunless.sunScatter = 0.0f;
    FrameInputs interior = input;
    interior.localLights.cameraInterior = true;
    interior.localLights.interiorBlend = 1.0f;
    FrameInputs halfInterior = interior;
    halfInterior.localLights.interiorBlend = kHalfInteriorBlend;
    FrameInputs moon = input;
    moon.lightIsMoon = true;
    Config moonOff = defaults;
    moonOff.moonScatter = kMoonScatterOff;
    Config moonOn = defaults;
    moonOn.moonScatter = kMoonScatterOn;
    Check(LightShadowFor(onScreen, full, BuildFogParams(input, sunless, nullptr)).strength == 0.0f &&
              LightShadowFor(onScreen, full, BuildFogParams(interior, full, nullptr)).strength == 0.0f &&
              LightShadowFor(onScreen, full, BuildFogParams(halfInterior, full, nullptr)).strength == 1.0f &&
              LightShadowFor(onScreen, full, BuildFogParams(moon, moonOff, nullptr)).strength == 0.0f &&
              LightShadowFor(onScreen, full, BuildFogParams(moon, moonOn, nullptr)).strength == 1.0f,
          "fog without direct light (SunScatter=0, a full interior blend, MoonScatter=0 at night) takes no shadow");

    FogParams flagged = {};
    flagged.layers[0].density = kFlaggedLayerDensity;
    flagged.layers[0].diffuse[0] = 1.0f;
    flagged.layers[0].shadowed = 1.0f;
    FogParams flaggedHalfUp = flagged;
    flaggedHalfUp.lightAboveHorizon = kHalfAboveHorizon;
    FogParams unlit = flagged;
    unlit.layers[0].shadowed = 0.0f;
    unlit.layers[0].diffuse[0] = 0.0f;
    Check(!FogScattersDirectLight(flagged) && FogScattersDirectLight(flaggedHalfUp) && !FogScattersDirectLight(unlit),
          "a shadowed Classic layer scatters direct light only while the light is above the horizon");
}

void CheckHaloOcclusionSetting(const std::wstring& outDir, const std::wstring& shippedIni)
{
    ConfigStore shipped;
    shipped.Load(NarrowPath(shippedIni));
    const std::string text = ReadText(shippedIni);
    const std::vector<std::string> lines = water_settings_checks::IniLines(text);
    Check(Config().haloOcclusion == 0.0f && shipped.Get().haloOcclusion == 0.0f &&
              std::count(lines.begin(), lines.end(), std::string("HaloOcclusion=0.0")) == 1 &&
              text.find("; Experimental, off by default and not in the settings window: how far terrain") !=
                  std::string::npos,
          "HaloOcclusion is off by default in the code and the shipped INI, which documents it as experimental");

    const std::wstring savedIni = FullPath(outDir + L"\\halo-occlusion.ini");
    CopyFileW(shippedIni.c_str(), savedIni.c_str(), FALSE);
    struct WrittenValue
    {
        const wchar_t* text;
        float expected;
    };
    const WrittenValue values[] = {{L"0.35", 0.35f}, {L"1", 1.0f}, {L"-2", 0.0f}, {L"7", 1.0f}, {L"abc", 0.0f}};
    bool parsed = true;
    for (const WrittenValue& value : values)
    {
        WritePrivateProfileStringW(L"Luxvelum", L"HaloOcclusion", value.text, savedIni.c_str());
        ConfigStore store;
        store.Load(NarrowPath(savedIni));
        parsed = parsed && store.Get().haloOcclusion == value.expected;
    }
    Check(parsed, "HaloOcclusion parses, clamps to 0..1 and keeps its default for an unreadable value");

    WritePrivateProfileStringW(L"Luxvelum", L"HaloOcclusion", L"0.0", savedIni.c_str());
    for (const wchar_t* removedKey : {L"LightShafts", L"WorldShadows"})
        WritePrivateProfileStringW(L"Luxvelum", removedKey, L"1", savedIni.c_str());
    ConfigStore withRemovedKeys;
    withRemovedKeys.Load(NarrowPath(savedIni));
    Check(SameLiveSettings(withRemovedKeys.Get(), shipped.Get()) && withRemovedKeys.Get().haloOcclusion == 0.0f,
          "LightShafts=1 and WorldShadows=1 stay ignored keys beside HaloOcclusion");

    ConfigStore store;
    store.Load(NarrowPath(savedIni));
    Config edited = store.Get();
    edited.haloOcclusion = kHalfStrength;
    const std::string changes = SettingChanges(store.Get(), edited);
    store.Apply(edited);
    const bool saved = store.Save();
    ConfigStore reloaded;
    reloaded.Load(NarrowPath(savedIni));
    std::printf("     the settings window's HaloOcclusion change logs \"%s\"\n", changes.c_str());
    Check(saved && reloaded.Get().haloOcclusion == kHalfStrength && changes == "HaloOcclusion 0 -> 0.5" &&
              ReadText(savedIni).find("\nHaloOcclusion=0.5") != std::string::npos &&
              !SameFogSettings(reloaded.Get(), shipped.Get()),
          "a HaloOcclusion change is logged, saved to the INI, read back and counts as a fog setting change");
}

struct RendererView
{
    D3DVIEWPORT9 world;
    Vec3 eye;
    float view[16];
    float projection[16];
    FrameInputs input;
};

RendererView LookingAt(Vec3 target)
{
    RendererView v = {};
    v.world = {0, 0, 1280, 688, 0.0f, 1.0f};
    v.eye = Add({0, 0, 9}, kGameLikeWorldOffset);
    const Vec3 at = Add(target, kGameLikeWorldOffset);
    CameraRelativeLookAt(v.eye, at, v.view);
    EngineProjection(1280.0f / 688.0f, v.projection);
    v.input = MakeInputs(v.view, v.projection, v.eye, at, v.world);
    return v;
}

LightOnScreen SunOnScreen(const RendererView& v)
{
    const float* m = v.view;
    const float* l = v.input.toLight;
    const float toLightInView[3] = {l[0] * m[0] + l[1] * m[4] + l[2] * m[8], l[0] * m[1] + l[1] * m[5] + l[2] * m[9],
                                    l[0] * m[2] + l[1] * m[6] + l[2] * m[10]};
    return ProjectLightOntoViewport(toLightInView, v.projection, v.world);
}

float HorizonRow(const RendererView& v)
{
    return (0.5f + v.view[10] / v.view[9] * v.projection[5] * 0.5f) * v.world.Height;
}

Config RadianceView(float haloOcclusion)
{
    Config config;
    config.temporal = 0.0f;
    config.noiseAmount = 0.0f;
    config.godRays = 0.0f;
    config.debugView = 1;
    config.haloOcclusion = haloOcclusion;
    return config;
}

struct ThinPosts
{
    std::vector<UINT> columns;
    float top = 0.0f;
    float bottom = 0.0f;
};

void DrawThinPosts(Harness& h, const RendererView& v, const ThinPosts& posts)
{
    const float rawDepth = RawDepthAtViewDistance(v.projection, kThinPostViewZ);
    for (UINT column : posts.columns)
    {
        const float left = static_cast<float>(column) - kPostEdgeBeforeColumn;
        h.DrawPretransformedQuadAtRawDepth(left, posts.top, left + 1.0f, posts.bottom, rawDepth);
    }
}

Image RenderBehindWall(Harness& h, const RendererView& v, const Config& config, float wallBottom, bool& rendered,
                       const ThinPosts& posts = {})
{
    vf_test_set_config(&config);
    h.BeginFrame();
    h.DrawScene(v.eye, v.view, v.projection, v.world);
    h.DrawPretransformedQuadAtRawDepth(0, 0, static_cast<float>(v.world.Width), wallBottom,
                                       RawDepthAtViewDistance(v.projection, kWallDistance));
    DrawThinPosts(h, v, posts);
    const char* skip = "";
    rendered = vf_test_render(&v.input, &skip) != 0 && rendered;
    Image image = Capture(h.dev);
    h.dev->EndScene();
    h.dev->Present(nullptr, nullptr, nullptr, nullptr);
    return image;
}

int LargestChannelDifference(const Image& a, const Image& b)
{
    if (a.w != b.w || a.h != b.h || a.bgra.size() != b.bgra.size())
        return 255;
    int worst = 0;
    for (size_t i = 0; i < a.bgra.size(); ++i)
        if (i % 4 != 3)
            worst = std::max(worst, std::abs(a.bgra[i] - b.bgra[i]));
    return worst;
}

struct SunlightKept
{
    int fewestSunCodes = 255;
    float largestShare = 0.0f;
};

void MeasureSunlightKept(SunlightKept& kept, const Image& unshadowed, const Image& shadowed, const Image& withoutSun,
                         UINT x, UINT y)
{
    const unsigned char* open = unshadowed.At(x, y);
    const unsigned char* blocked = shadowed.At(x, y);
    const unsigned char* reference = withoutSun.At(x, y);
    int channel = 0;
    for (int c = 1; c < 3; ++c)
        if (open[c] - reference[c] > open[channel] - reference[channel])
            channel = c;
    const int sunCodes = open[channel] - reference[channel];
    kept.fewestSunCodes = std::min(kept.fewestSunCodes, sunCodes);
    kept.largestShare = std::max(kept.largestShare, static_cast<float>(blocked[channel] - reference[channel]) /
                                                        static_cast<float>(std::max(sunCodes, 1)));
}

void CheckHaloOcclusionInTheRenderer(Harness& h)
{
    Config saved;
    vf_test_get_config(&saved);
    const RendererView ahead = LookingAt({100, 2, 4});
    const LightOnScreen sun = SunOnScreen(ahead);
    const float horizonRow = HorizonRow(ahead);
    const float wallBottom = (sun.pixel[1] + horizonRow) * 0.5f;
    Config sunless = RadianceView(0.0f);
    sunless.sunScatter = 0.0f;
    bool rendered = true;
    const Image unshadowed = RenderBehindWall(h, ahead, RadianceView(0.0f), wallBottom, rendered);
    const Image shadowed = RenderBehindWall(h, ahead, RadianceView(1.0f), wallBottom, rendered);
    const Image repeated = RenderBehindWall(h, ahead, RadianceView(1.0f), wallBottom, rendered);
    const Image withoutSun = RenderBehindWall(h, ahead, sunless, wallBottom, rendered);
    SunlightKept ground;
    for (float rowBelowHorizon : {30.0f, 60.0f})
        for (float columnFromSun : {-200.0f, 0.0f, 200.0f})
        {
            const float lastColumn = static_cast<float>(ahead.world.Width) - 20.0f;
            const UINT x = static_cast<UINT>(std::clamp(sun.pixel[0] + columnFromSun, 20.0f, lastColumn));
            const UINT y = static_cast<UINT>(horizonRow + rowBelowHorizon);
            MeasureSunlightKept(ground, unshadowed, shadowed, withoutSun, x, y);
        }
    std::printf("     wall at %.0f yd above row %.0f (sun row %.0f, horizon %.0f): the ground's fog keeps at most %.2f "
                "of its sunlight, at least %d/255 of it unshadowed\n",
                kWallDistance, wallBottom, sun.pixel[1], horizonRow, ground.largestShare, ground.fewestSunCodes);
    Check(rendered && sun.inFront && sun.pixel[1] < wallBottom && ground.fewestSunCodes >= kMinSunCodes &&
              ground.largestShare <= kMaxSunShareBehindWall,
          "the renderer shadows the sunlight in the fog whose light path a wall in front of the sun hides");
    Check(rendered && LargestChannelDifference(shadowed, repeated) == 0,
          "two frames of the shadowed fog are identical with Temporal=0");

    const RendererView away = LookingAt({-100, -2, 4});
    const float awayWallBottom = static_cast<float>(away.world.Height) * 0.5f;
    bool renderedAway = true;
    const Image awayShadowed = RenderBehindWall(h, away, RadianceView(1.0f), awayWallBottom, renderedAway);
    const Image awayUnshadowed = RenderBehindWall(h, away, RadianceView(0.0f), awayWallBottom, renderedAway);
    Check(renderedAway && !SunOnScreen(away).inFront && LargestChannelDifference(awayShadowed, awayUnshadowed) == 0,
          "with the sun behind the camera HaloOcclusion leaves the frame unchanged");
    vf_test_set_config(&saved);
}

UINT UntappedColumnNear(float x)
{
    return static_cast<UINT>(std::floor(x / kUntappedColumnPeriod) * kUntappedColumnPeriod);
}

void CheckHaloOcclusionAtFullResolutionWithTemporal(Harness& h)
{
    Config saved;
    vf_test_get_config(&saved);
    const RendererView ahead = LookingAt({100, 2, 4});
    const LightOnScreen sun = SunOnScreen(ahead);
    const float horizonRow = HorizonRow(ahead);
    const float wallBottom = (sun.pixel[1] + horizonRow) * 0.5f;
    ThinPosts posts;
    for (float columnFromSun : kThinPostColumnsFromSun)
        posts.columns.push_back(UntappedColumnNear(sun.pixel[0] + columnFromSun));
    posts.top = wallBottom + kThinPostRowMargin;
    posts.bottom = horizonRow - kThinPostRowMargin;
    Config filtered = RadianceView(1.0f);
    filtered.temporal = Config().temporal;
    Config sunless = RadianceView(0.0f);
    sunless.sunScatter = 0.0f;
    bool rendered = true;
    const Image unshadowed = RenderBehindWall(h, ahead, RadianceView(0.0f), wallBottom, rendered, posts);
    const Image withoutSun = RenderBehindWall(h, ahead, sunless, wallBottom, rendered, posts);
    const Image unfiltered = RenderBehindWall(h, ahead, RadianceView(1.0f), wallBottom, rendered, posts);
    SunlightKept postFog;
    int largestDifference = 0;
    for (int frame = 0; frame < kFilteredFrames; ++frame)
    {
        const Image shadowed = RenderBehindWall(h, ahead, filtered, wallBottom, rendered, posts);
        for (UINT x : posts.columns)
            for (UINT y = static_cast<UINT>(std::ceil(posts.top)) + 1; y + 1 < posts.bottom; ++y)
            {
                MeasureSunlightKept(postFog, unshadowed, shadowed, withoutSun, x, y);
                for (int c = 0; c < 3; ++c)
                    largestDifference = std::max(largestDifference, std::abs(shadowed.At(x, y)[c] -
                                                                             unfiltered.At(x, y)[c]));
            }
    }
    std::printf("     posts at %.0f yd in columns %u and %u, rows %.0f to %.0f: with Temporal=%.2f their fog keeps at "
                "most %.2f of its sunlight, at least %d/255 of it unshadowed, %d/255 from the frame with Temporal=0\n",
                kThinPostViewZ, posts.columns.front(), posts.columns.back(), posts.top, posts.bottom, filtered.temporal,
                postFog.largestShare, postFog.fewestSunCodes, largestDifference);
    Check(rendered && posts.top + 2 * kThinPostRowMargin < posts.bottom && postFog.fewestSunCodes >= kMinSunCodes &&
              postFog.largestShare <= kMaxSunShareBehindWall && largestDifference == 0,
          "with Temporal on, the composite marches the thin posts the low-resolution taps miss with the halo shadow, "
          "as without Temporal");
    vf_test_set_config(&saved);
}
}
