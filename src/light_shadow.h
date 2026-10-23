#pragma once

#include "config.h"
#include "fog_model.h"

#include <d3d9.h>

constexpr float kLightInFrontViewZ = 0.05f;
constexpr float kLightShadowFullViewZ = 0.2f;
constexpr float kOccluderThicknessShare = 0.25f;

struct LightOnScreen
{
    bool inFront;
    float viewZ;
    float ndc[2];
    float pixel[2];
};

struct LightShadowConstants
{
    float lightPixel[2];
    float strength;
    float occluderThicknessShare;
};

static_assert(sizeof(LightShadowConstants) == 4 * sizeof(float), "LightShadowConstants uploads as one float4 register");

LightOnScreen ProjectLightOntoViewport(const float* toLightInView, const float* glProjection, const D3DVIEWPORT9& vp);
bool FogScattersDirectLight(const FogParams& fog);
float LightShadowStrength(float haloOcclusion, float toLightViewZ, const FogParams& fog);
LightShadowConstants LightShadowFor(const LightOnScreen& light, const Config& cfg, const FogParams& fog);
