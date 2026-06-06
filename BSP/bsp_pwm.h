#pragma once

#include <stdint.h>
#include "Common/common_types.h"

typedef struct
{
    uint32_t channel;
    uint32_t timer_freq_hz;
    uint32_t pwm_freq_hz;
    float duty_cycle;
} BSP_PWM_ChannelConfig_t;

Status_t BSP_PWM_Init(void);
Status_t BSP_PWM_SetFrequency(uint32_t channel, uint32_t freq_hz);
Status_t BSP_PWM_SetDutyCycle(uint32_t channel, float duty_cycle);
Status_t BSP_PWM_Start(uint32_t channel);
Status_t BSP_PWM_Stop(uint32_t channel);
Status_t BSP_PWM_SetChannelConfig(const BSP_PWM_ChannelConfig_t *config);
const BSP_PWM_ChannelConfig_t *BSP_PWM_GetChannelConfig(uint32_t channel);
