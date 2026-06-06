#pragma once

#include <stdint.h>
#include "Common/common_types.h"

/*
 * MCP9808 default 7-bit I2C address is 0x18.
 * The driver checks manufacturer/device ID during init.
 */

Status_t MCP9808_Init(void);
Status_t MCP9808_ReadTemperature(float *celsius);
