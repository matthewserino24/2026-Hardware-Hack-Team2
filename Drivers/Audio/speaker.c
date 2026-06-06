#include "Drivers/Audio/speaker.h"
#include "BSP/bsp_pwm.h"

#define SPEAKER_DEFAULT_CHANNEL        (0u)
#define SPEAKER_DEFAULT_FREQ_HZ        (1000u)
#define SPEAKER_DEFAULT_DUTY_PERCENT   (50u)

static Speaker_Config_t s_config = {
    .channel = SPEAKER_DEFAULT_CHANNEL,
    .default_freq_hz = SPEAKER_DEFAULT_FREQ_HZ,
    .default_duty_percent = SPEAKER_DEFAULT_DUTY_PERCENT
};

static Status_t speaker_apply_tone(uint16_t freq_hz, uint8_t duty_percent)
{
    BSP_PWM_ChannelConfig_t pwm_cfg;
    pwm_cfg.channel = s_config.channel;
    pwm_cfg.timer_freq_hz = 0u;
    pwm_cfg.pwm_freq_hz = freq_hz;
    pwm_cfg.duty_cycle = (float)duty_percent / 100.0f;

    if (BSP_PWM_SetChannelConfig(&pwm_cfg) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_PWM_SetFrequency(s_config.channel, freq_hz) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_PWM_SetDutyCycle(s_config.channel, pwm_cfg.duty_cycle) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (BSP_PWM_Start(s_config.channel) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    return STATUS_OK;
}

Status_t Speaker_Init(void)
{
    if (BSP_PWM_Init() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    return BSP_PWM_Stop(s_config.channel);
}

Status_t Speaker_Beep(uint16_t freq_hz, uint16_t duration_ms)
{
    if (speaker_apply_tone(freq_hz, s_config.default_duty_percent) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    /*
     * Duration handling is intentionally left as a thin skeleton.
     * In the CubeMX project this can be driven by a timer callback or a delay
     * service without changing the API.
     */
    (void)duration_ms;
    return STATUS_OK;
}

Status_t Speaker_SetTone(uint16_t freq_hz)
{
    return speaker_apply_tone(freq_hz, s_config.default_duty_percent);
}

Status_t Speaker_Stop(void)
{
    return BSP_PWM_Stop(s_config.channel);
}

Status_t Speaker_SetVolume(uint8_t duty_percent)
{
    if (duty_percent > 100u)
    {
        return STATUS_ERROR;
    }

    s_config.default_duty_percent = duty_percent;
    return BSP_PWM_SetDutyCycle(s_config.channel, (float)duty_percent / 100.0f);
}

Status_t Speaker_SetConfig(const Speaker_Config_t *config)
{
    if (config == 0)
    {
        return STATUS_ERROR;
    }

    s_config = *config;
    return STATUS_OK;
}

const Speaker_Config_t *Speaker_GetConfig(void)
{
    return &s_config;
}
