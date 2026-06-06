#include "BSP/bsp_i2c.h"

Status_t BSP_I2C_Init(void)
{
    return STATUS_OK;
}

Status_t BSP_I2C_Write(uint8_t dev_addr, uint8_t reg_addr, const uint8_t *data, uint16_t len)
{
    (void)dev_addr;
    (void)reg_addr;
    (void)data;
    (void)len;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_I2C_Read(uint8_t dev_addr, uint8_t reg_addr, uint8_t *data, uint16_t len)
{
    (void)dev_addr;
    (void)reg_addr;
    (void)data;
    (void)len;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_I2C_WriteRaw(uint8_t dev_addr, const uint8_t *data, uint16_t len)
{
    (void)dev_addr;
    (void)data;
    (void)len;
    return STATUS_UNSUPPORTED;
}
