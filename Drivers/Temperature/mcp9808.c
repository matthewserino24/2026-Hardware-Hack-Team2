#include "Drivers/Temperature/mcp9808.h"
#include "BSP/bsp_i2c.h"

#define MCP9808_I2C_ADDR_7BIT          (0x18u)
#define MCP9808_REG_CONFIG             (0x01u)
#define MCP9808_REG_AMBIENT_TEMP       (0x05u)
#define MCP9808_REG_MANUF_ID           (0x06u)
#define MCP9808_REG_DEVICE_ID          (0x07u)

#define MCP9808_MANUF_ID_VALUE         (0x0054u)
#define MCP9808_DEVICE_ID_VALUE        (0x0400u)

static Status_t mcp9808_read_u16(uint8_t reg, uint16_t *value)
{
    uint8_t buf[2] = {0};
    Status_t status = BSP_I2C_Read(MCP9808_I2C_ADDR_7BIT, reg, buf, 2u);
    if (status != STATUS_OK)
    {
        return status;
    }

    *value = (uint16_t)(((uint16_t)buf[0] << 8) | buf[1]);
    return STATUS_OK;
}

static Status_t mcp9808_write_u16(uint8_t reg, uint16_t value)
{
    uint8_t buf[2];
    buf[0] = (uint8_t)((value >> 8) & 0xFFu);
    buf[1] = (uint8_t)(value & 0xFFu);
    return BSP_I2C_Write(MCP9808_I2C_ADDR_7BIT, reg, buf, 2u);
}

Status_t MCP9808_Init(void)
{
    uint16_t manuf_id = 0;
    uint16_t device_id = 0;

    if (BSP_I2C_Init() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (mcp9808_read_u16(MCP9808_REG_MANUF_ID, &manuf_id) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (mcp9808_read_u16(MCP9808_REG_DEVICE_ID, &device_id) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (manuf_id != MCP9808_MANUF_ID_VALUE)
    {
        return STATUS_ERROR;
    }

    if ((device_id & 0xFFF0u) != MCP9808_DEVICE_ID_VALUE)
    {
        return STATUS_ERROR;
    }

    /*
     * Leave config at power-up default for now.
     * This write path is here so low-power / alert configuration can be added
     * later without changing the driver shape.
     */
    if (mcp9808_write_u16(MCP9808_REG_CONFIG, 0x0000u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    return STATUS_OK;
}

Status_t MCP9808_ReadTemperature(float *celsius)
{
    if (celsius == 0)
    {
        return STATUS_ERROR;
    }

    uint16_t raw = 0;
    if (mcp9808_read_u16(MCP9808_REG_AMBIENT_TEMP, &raw) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    /*
     * Temperature format:
     * bits [15:13] are flags, [12] sign, [11:0] temperature data
     * Resolution is 0.0625 C per LSB.
     */
    uint16_t temp_bits = raw & 0x0FFFu;
    float temp = (float)(temp_bits & 0x0FFFu) / 16.0f;
    if ((raw & 0x1000u) != 0u)
    {
        temp -= 256.0f;
    }

    *celsius = temp;
    return STATUS_OK;
}
