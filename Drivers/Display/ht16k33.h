#pragma once

#include <stdint.h>
#include "Common/common_types.h"

/*
 * HT16K33 LED matrix driver skeleton.
 * Default I2C address is usually 0x70, but it can vary depending on address pins.
 * DisplayNumber() renders a compact 3x5 glyph on an 8x8 matrix.
 */

typedef struct
{
    uint8_t i2c_addr_7bit;
    uint8_t brightness;     // 0..15
    uint8_t display_on;     // 0 or 1
} HT16K33_Config_t;

Status_t HT16K33_Init(void);
Status_t HT16K33_Clear(void);
Status_t HT16K33_SetPixel(uint8_t x, uint8_t y, uint8_t on);
Status_t HT16K33_SetBrightness(uint8_t brightness);
Status_t HT16K33_DisplayNumber(int16_t number);
Status_t HT16K33_SetConfig(const HT16K33_Config_t *config);
const HT16K33_Config_t *HT16K33_GetConfig(void);
