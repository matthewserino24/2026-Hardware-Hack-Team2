#pragma once

#include "Services/system_service.h"

void AppState_Init(void);
SystemState_t AppState_Get(void);
void AppState_Set(SystemState_t state);

