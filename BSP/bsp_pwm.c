#include "BSP/bsp_pwm.h"

#define BSP_PWM_MAX_CHANNELS  (4u)

static BSP_PWM_ChannelConfig_t s_channels[BSP_PWM_MAX_CHANNELS] = {
    {0u, 0u, 0u, 0.5f},
    {1u, 0u, 0u, 0.5f},
    {2u, 0u, 0u, 0.5f},
    {3u, 0u, 0u, 0.5f},
};

Status_t BSP_PWM_Init(void)
{
    return STATUS_OK;
}

Status_t BSP_PWM_SetFrequency(uint32_t channel, uint32_t freq_hz)
{
    (void)channel;
    (void)freq_hz;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_PWM_SetDutyCycle(uint32_t channel, float duty_cycle)
{
    (void)channel;
    (void)duty_cycle;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_PWM_Start(uint32_t channel)
{
    (void)channel;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_PWM_Stop(uint32_t channel)
{
    (void)channel;
    return STATUS_UNSUPPORTED;
}

Status_t BSP_PWM_SetChannelConfig(const BSP_PWM_ChannelConfig_t *config)
{
    if (config == 0)
    {
        return STATUS_ERROR;
    }

    if (config->channel >= BSP_PWM_MAX_CHANNELS)
    {
        return STATUS_ERROR;
    }

    s_channels[config->channel] = *config;
    return STATUS_OK;
}

const BSP_PWM_ChannelConfig_t *BSP_PWM_GetChannelConfig(uint32_t channel)
{
    if (channel >= BSP_PWM_MAX_CHANNELS)
    {
        return 0;
    }

    return &s_channels[channel];
}
