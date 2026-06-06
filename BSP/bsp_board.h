#pragma once

#include <stdint.h>

void BSP_Board_Init(void);
uint32_t BSP_GetTickMs(void);
void BSP_DelayMs(uint32_t ms);

