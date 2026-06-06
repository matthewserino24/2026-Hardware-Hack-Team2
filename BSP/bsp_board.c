#include "BSP/bsp_board.h"

static uint32_t s_tick_ms = 0;

void BSP_Board_Init(void)
{
    s_tick_ms = 0;
}

uint32_t BSP_GetTickMs(void)
{
    return s_tick_ms;
}

void BSP_DelayMs(uint32_t ms)
{
    s_tick_ms += ms;
}

