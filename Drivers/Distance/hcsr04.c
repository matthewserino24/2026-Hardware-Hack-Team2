#include "Drivers/Distance/hcsr04.h"
#include "BSP/bsp_gpio.h"
#include "BSP/bsp_timer.h"
#include "Config/pinmap.h"

#define HCSR04_SOUND_SPEED_CM_PER_US  (0.0343f)
#define HCSR04_DEFAULT_TIMEOUT_US     (30000u)
#define HCSR04_TRIGGER_PULSE_US       (10u)

static HCSR04_Config_t s_config = {
    .trig_port = 0u,
    .trig_pin = 0u,
    .echo_port = 0u,
    .echo_pin = 0u,
    .echo_timer_channel = 0u,
    .timeout_us = HCSR04_DEFAULT_TIMEOUT_US
};

static uint32_t s_echo_rising_us = 0u;
static uint32_t s_echo_falling_us = 0u;
static uint8_t s_waiting_for_falling = 0u;

static void hcsr04_load_default_config(void)
{
    s_config.trig_port = 0u;
    s_config.trig_pin = 0u;
    s_config.echo_port = 0u;
    s_config.echo_pin = 0u;
    s_config.echo_timer_channel = 0u;
    s_config.timeout_us = HCSR04_DEFAULT_TIMEOUT_US;
}

Status_t HCSR04_Init(void)
{
    if (BSP_GPIO_Init() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_Timer_Init() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    hcsr04_load_default_config();
    s_waiting_for_falling = 0u;
    s_echo_rising_us = 0u;
    s_echo_falling_us = 0u;
    return STATUS_OK;
}

Status_t HCSR04_ReadDistanceCm(float *distance_cm)
{
    if (distance_cm == 0)
    {
        return STATUS_ERROR;
    }

    if (HCSR04_Trigger() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    uint32_t start_us = BSP_Timer_GetMicros();
    while ((s_echo_falling_us <= s_echo_rising_us) &&
           ((BSP_Timer_GetMicros() - start_us) < s_config.timeout_us))
    {
        /* Wait for the ISR/callback path to capture the echo pulse. */
    }

    if (s_echo_falling_us <= s_echo_rising_us)
    {
        return STATUS_TIMEOUT;
    }

    uint32_t pulse_width_us = s_echo_falling_us - s_echo_rising_us;
    *distance_cm = (float)pulse_width_us * HCSR04_SOUND_SPEED_CM_PER_US * 0.5f;
    return STATUS_OK;
}

Status_t HCSR04_Trigger(void)
{
    if (BSP_GPIO_Write(s_config.trig_port, s_config.trig_pin, GPIO_LEVEL_LOW) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_Timer_DelayUs(2u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_GPIO_Write(s_config.trig_port, s_config.trig_pin, GPIO_LEVEL_HIGH) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_Timer_DelayUs(HCSR04_TRIGGER_PULSE_US) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_GPIO_Write(s_config.trig_port, s_config.trig_pin, GPIO_LEVEL_LOW) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    s_waiting_for_falling = 0u;
    s_echo_rising_us = 0u;
    s_echo_falling_us = 0u;
    return STATUS_OK;
}

Status_t HCSR04_CaptureEdge(HCSR04_Edge_t edge)
{
    uint32_t now_us = BSP_Timer_GetMicros();

    if (edge == HCSR04_EDGE_RISING)
    {
        s_echo_rising_us = now_us;
        s_waiting_for_falling = 1u;
        return STATUS_OK;
    }

    if (s_waiting_for_falling == 0u)
    {
        return STATUS_ERROR;
    }

    s_echo_falling_us = now_us;
    s_waiting_for_falling = 0u;
    return STATUS_OK;
}

Status_t HCSR04_SetConfig(const HCSR04_Config_t *config)
{
    if (config == 0)
    {
        return STATUS_ERROR;
    }

    s_config = *config;
    return STATUS_OK;
}

const HCSR04_Config_t *HCSR04_GetConfig(void)
{
    return &s_config;
}
