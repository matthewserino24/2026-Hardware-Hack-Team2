#pragma once

#include <stdint.h>
#include "Common/common_types.h"

typedef struct
{
    uint32_t trig_port;
    uint32_t trig_pin;
    uint32_t echo_port;
    uint32_t echo_pin;
    uint32_t echo_timer_channel;
    uint32_t timeout_us;
} HCSR04_Config_t;

typedef enum
{
    HCSR04_EDGE_RISING = 0,
    HCSR04_EDGE_FALLING = 1
} HCSR04_Edge_t;

Status_t HCSR04_Init(void);
Status_t HCSR04_ReadDistanceCm(float *distance_cm);

Status_t HCSR04_Trigger(void);
Status_t HCSR04_CaptureEdge(HCSR04_Edge_t edge);
Status_t HCSR04_SetConfig(const HCSR04_Config_t *config);
const HCSR04_Config_t *HCSR04_GetConfig(void);
