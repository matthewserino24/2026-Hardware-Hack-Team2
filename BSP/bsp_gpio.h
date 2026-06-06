#pragma once

#include <stdint.h>
#include "Common/common_types.h"

typedef enum
{
    GPIO_LEVEL_LOW = 0,
    GPIO_LEVEL_HIGH = 1
} GPIO_Level_t;

Status_t BSP_GPIO_Init(void);
Status_t BSP_GPIO_Write(uint32_t port, uint32_t pin, GPIO_Level_t level);
Status_t BSP_GPIO_Read(uint32_t port, uint32_t pin, GPIO_Level_t *level);

