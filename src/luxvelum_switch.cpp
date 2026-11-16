#include "luxvelum_switch.h"

#include <atomic>

namespace
{
constexpr unsigned kRequestedOff = 1u;

std::atomic<unsigned> g_request{0u};
bool g_switchedOff = false;
}

void FlipLuxVelumSwitch()
{
    g_request.fetch_xor(kRequestedOff);
}

void SwitchLuxVelumOn()
{
    g_request.store(0u);
}

bool LuxVelumSwitchFlippedOff()
{
    return (g_request.load() & kRequestedOff) != 0;
}

bool LatchLuxVelumSwitch()
{
    const bool off = LuxVelumSwitchFlippedOff();
    const bool changed = off != g_switchedOff;
    g_switchedOff = off;
    return changed;
}

bool LuxVelumSwitchedOff()
{
    return g_switchedOff;
}
