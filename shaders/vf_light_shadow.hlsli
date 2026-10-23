float4 cLightShadow : register(c10);

#ifndef SHADOW_TAPS
#define SHADOW_TAPS 16
#endif

#ifndef THIN_OCCLUDER_SHADOWS
#define THIN_OCCLUDER_SHADOWS 1
#endif

static const int kShadowTaps = SHADOW_TAPS;
static const bool kShadowsBehindThinOccluders = THIN_OCCLUDER_SHADOWS;
static const float kSolidOccluderShareOfSurface = 0.5;
static const float kMinOccluderThickness = 2;
static const float kFirstTapPixels = 1;
static const float kMaxFirstTapShareOfLine = 0.5;
static const float kUnshadowedDistance = 1e30;
static const float kMinLightStep = 1e-6;
static const float kMinRemainingShareOfLine = 1e-6;
static const float kMinShadowedStepLength = 1e-4;

struct LightShadow
{
    float solidFrom;
    float solidTo;
    float thinFrom;
    float thinTo;
};

float2 LightPixel()
{
    return cLightShadow.xy;
}

float LightShadowStrength()
{
    return cLightShadow.z;
}

float OccluderThicknessShare()
{
    return cLightShadow.w;
}

float LineInsideViewport(float2 pixel, float2 toLight)
{
    float2 edge = toLight < 0 ? ViewportOrigin() + 0.5 : ViewportLastPixelCentre();
    float2 reach = abs(edge - pixel) / max(abs(toLight), kMinLightStep);
    return min(1, min(reach.x, reach.y));
}

LightShadow UnshadowedRay()
{
    LightShadow shadow;
    shadow.solidFrom = kUnshadowedDistance;
    shadow.solidTo = kUnshadowedDistance;
    shadow.thinFrom = kUnshadowedDistance;
    shadow.thinTo = kUnshadowedDistance;
    return shadow;
}

LightShadow LightShadowAlongRay(float2 pixel, float depth, float distancePerViewZ, float jitter)
{
    LightShadow shadow = UnshadowedRay();
    [branch] if (LightShadowStrength() > 0)
    {
        float thinFrom = kUnshadowedDistance;
        float thinTo = 0;
        bool sky = IsSky(depth);
        float surfaceViewZ = sky ? kUnshadowedDistance : LinearDepth(depth);
        bool distantTerrain = !sky && BeyondFarClip(depth);
        float solidFromViewZ = kSolidOccluderShareOfSurface * surfaceViewZ;
        float lastSolidViewZ = distantTerrain ? kUnshadowedDistance : surfaceViewZ;
        float2 toLight = LightPixel() - pixel;
        float lineInViewport = LineInsideViewport(pixel, toLight);
        float firstTap = min(kFirstTapPixels / max(length(toLight), kMinLightStep),
                             kMaxFirstTapShareOfLine * lineInViewport);
        float tapSpacing = (lineInViewport - firstTap) / kShadowTaps;
        [loop] for (int k = 0; k < kShadowTaps; k++)
        {
            float lineFraction = firstTap + (k + jitter) * tapSpacing;
            float tapDepth = SampleDepth(sDepth, pixel + toLight * lineFraction);
            float remaining = max(1 - lineFraction, kMinRemainingShareOfLine);
            float occluderViewZ = LinearDepth(tapDepth);
            bool open = IsSky(tapDepth) || (distantTerrain && BeyondFarClip(tapDepth));
            bool solid = !open && occluderViewZ >= solidFromViewZ;
            bool thin = !open && !solid;
            bool thinShadow = kShadowsBehindThinOccluders && thin;
            float hiddenViewZ = solid ? occluderViewZ : (thin ? lastSolidViewZ : kUnshadowedDistance);
            float hiddenFrom = hiddenViewZ * remaining;
            float thickness = max(kMinOccluderThickness, OccluderThicknessShare() * occluderViewZ);
            shadow.solidFrom = min(shadow.solidFrom, hiddenFrom);
            thinFrom = thinShadow ? min(thinFrom, occluderViewZ * remaining) : thinFrom;
            thinTo = thinShadow ? max(thinTo, (occluderViewZ + thickness) * remaining) : thinTo;
            lastSolidViewZ = open ? kUnshadowedDistance : (solid ? occluderViewZ : lastSolidViewZ);
        }
        shadow.solidTo = surfaceViewZ * distancePerViewZ;
        shadow.solidFrom = min(shadow.solidFrom * distancePerViewZ, shadow.solidTo);
        shadow.thinTo = min(thinTo * distancePerViewZ, shadow.solidFrom);
        shadow.thinFrom = min(thinFrom * distancePerViewZ, shadow.thinTo);
    }
    return shadow;
}

float LitShare(LightShadow shadow, float stepStart, float stepEnd)
{
    float litShare = 1;
    [branch] if (LightShadowStrength() > 0)
    {
        float stepLength = max(stepEnd - stepStart, kMinShadowedStepLength);
        float behindSolid = saturate((min(stepEnd, shadow.solidTo) - max(stepStart, shadow.solidFrom)) / stepLength);
        float2 thinInStep = saturate((float2(shadow.thinTo, shadow.thinFrom) - stepStart) / stepLength);
        float insideThin = kShadowsBehindThinOccluders ? thinInStep.x - thinInStep.y : 0;
        litShare = 1 - LightShadowStrength() * (behindSolid + insideThin);
    }
    return litShare;
}
