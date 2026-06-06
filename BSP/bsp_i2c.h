#pragma once

#include <stdint.h>
#include "Common/common_types.h"

/*
 * Device-facing I2C abstraction.
 * Implement these functions on top of STM32 HAL_I2C_* in the CubeMX project.
 */

Status_t BSP_I2C_Init(void);
Status_t BSP_I2C_Write(uint8_t dev_addr, uint8_t reg_addr, const uint8_t *data, uint16_t len);
Status_t BSP_I2C_Read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len);

/*
 * For devices like HT16K33 that use command-only writes without a register
 * address, keep this raw write path available at the BSP layer.
 */
Status_t BSP_I2C_WriteRaw(uint8_t dev_addr, const uint8_t *data, uint16_t len);
