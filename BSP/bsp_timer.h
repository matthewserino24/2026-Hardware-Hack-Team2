#pragma once

#include <stdint.h>
#include "Common/common_types.h"

Status_t BSP_Timer_Init(void);
uint32_t BSP_Timer_GetMicros(void);
Status_t BSP_Timer_DelayUs(uint32_t us);

