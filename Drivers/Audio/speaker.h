#pragma once

#include <stdint.h>
#include "Common/common_types.h"

typedef struct
{
    uint32_t channel;
    uint16_t default_freq_hz;
    uint8_t default_duty_percent;
} Speaker_Config_t;

Status_t Speaker_Init(void);
Status_t Speaker_Beep(uint16_t freq_hz, uint16_t duration_ms);
Status_t Speaker_SetTone(uint16_t freq_hz);
Status_t Speaker_Stop(void);
Status_t Speaker_SetVolume(uint8_t duty_percent);
Status_t Speaker_SetConfig(const Speaker_Config_t *config);
const Speaker_Config_t *Speaker_GetConfig(void);
