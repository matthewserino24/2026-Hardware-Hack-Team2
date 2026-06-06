#pragma once

typedef enum
{
    STATE_INIT = 0,
    STATE_IDLE = 1,
    STATE_ACTIVE = 2,
    STATE_ALERT = 3
} SystemState_t;

void SystemService_Init(void);
SystemState_t SystemService_GetState(void);
void SystemService_SetState(SystemState_t state);

