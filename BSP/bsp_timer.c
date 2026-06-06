#include "BSP/bsp_timer.h"

static uint32_t s_time_us = 0;

Status_t BSP_Timer_Init(void)
{
    s_time_us = 0;
    return STATUS_OK;
}

uint32_t BSP_Timer_GetMicros(void)
{
    return s_time_us;
}

Status_t BSP_Timer_DelayUs(uint32_t us)
{
    s_time_us += us;
    return STATUS_OK;
}
