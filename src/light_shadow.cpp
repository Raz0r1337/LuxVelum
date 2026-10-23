#include "light_shadow.h"

#include <algorithm>
#include <iterator>

namespace
{
float SmoothStep(float edge0, float edge1, float x)
{
    const float t = std::clamp((x - edge0) / (edge1 - edge0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

bool LayerScattersDirectLight(const FogLayer& layer, float lightAboveHorizon)
{
    const float peakDiffuse = std::max(layer.diffuse[0], std::max(layer.diffuse[1], layer.diffuse[2]));
    const float horizonShadow = layer.shadowed * (1.0f - lightAboveHorizon);
    return layer.density > 0.0f && peakDiffuse > 0.0f && horizonShadow < 1.0f;
}
}

LightOnScreen ProjectLightOntoViewport(const float* toLightInView, const float* glProjection, const D3DVIEWPORT9& vp)
{
    LightOnScreen light = {};
    light.viewZ = toLightInView[2];
    light.inFront = light.viewZ > kLightInFrontViewZ;
    if (!light.inFront)
        return light;
    light.ndc[0] = toLightInView[0] / toLightInView[2] * glProjection[0] + glProjection[8];
    light.ndc[1] = toLightInView[1] / toLightInView[2] * glProjection[5] + glProjection[9];
    light.pixel[0] = vp.X + (light.ndc[0] * 0.5f + 0.5f) * vp.Width;
    light.pixel[1] = vp.Y + (0.5f - light.ndc[1] * 0.5f) * vp.Height;
    return light;
}

bool FogScattersDirectLight(const FogParams& fog)
{
    return std::any_of(std::begin(fog.layers), std::end(fog.layers), [&fog](const FogLayer& layer) {
        return LayerScattersDirectLight(layer, fog.lightAboveHorizon);
    });
}

float LightShadowStrength(float haloOcclusion, float toLightViewZ, const FogParams& fog)
{
    if (!(haloOcclusion > 0.0f) || !(toLightViewZ > kLightInFrontViewZ) || !FogScattersDirectLight(fog))
        return 0.0f;
    return std::min(haloOcclusion, 1.0f) * SmoothStep(kLightInFrontViewZ, kLightShadowFullViewZ, toLightViewZ);
}

LightShadowConstants LightShadowFor(const LightOnScreen& light, const Config& cfg, const FogParams& fog)
{
    LightShadowConstants constants = {};
    constants.lightPixel[0] = light.pixel[0];
    constants.lightPixel[1] = light.pixel[1];
    constants.strength = light.inFront ? LightShadowStrength(cfg.haloOcclusion, light.viewZ, fog) : 0.0f;
    constants.occluderThicknessShare = kOccluderThicknessShare;
    return constants;
}
