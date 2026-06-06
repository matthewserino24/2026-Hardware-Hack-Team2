#pragma once

#include <stdint.h>
#include "Common/common_types.h"

Status_t SG90_Init(void);
Status_t SG90_SetAngle(float angle_deg);
Status_t SG90_SetPulseUs(uint16_t pulse_us);

