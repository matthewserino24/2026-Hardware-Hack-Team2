#include "App/app_state.h"

static SystemState_t s_app_state = STATE_INIT;

void AppState_Init(void)
{
    s_app_state = STATE_IDLE;
}

SystemState_t AppState_Get(void)
{
    return s_app_state;
}

void AppState_Set(SystemState_t state)
{
    s_app_state = state;
}

