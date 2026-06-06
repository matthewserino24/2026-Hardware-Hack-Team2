#include "BSP/bsp_gpio.h"

Status_t BSP_GPIO_Init(void)
{
    return STATUS_OK;
}

Status_t BSP_GPIO_Write(uint32_t port, uint32_t pin, GPIO_Level_t level)
{
    (void)port;
    (void)pin;
    (void)level;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_GPIO_Read(uint32_t port, uint32_t pin, GPIO_Level_t *level)
{
    (void)port;
    (void)pin;
    if (level == 0)
    {
        return STATUS_ERROR;
    }
    *level = GPIO_LEVEL_LOW;
    return STATUS_UNSUPPORTED;
}

