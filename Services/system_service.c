#include "Services/system_service.h"

static SystemState_t s_state = STATE_INIT;

void SystemService_Init(void)
{
    s_state = STATE_IDLE;
}

SystemState_t SystemService_GetState(void)
{
    return s_state;
}

void SystemService_SetState(SystemState_t state)
{
    s_state = state;
}

