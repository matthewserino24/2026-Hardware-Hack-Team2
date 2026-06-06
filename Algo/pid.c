#include "Algo/pid.h"

static float clampf(float value, float min_value, float max_value)
{
    if (value < min_value)
    {
        return min_value;
    }
    if (value > max_value)
    {
        return max_value;
    }
    return value;
}

void PID_Init(PID_t *pid, float kp, float ki, float kd, float out_min, float out_max)
{
    if (pid == 0)
    {
        return;
    }

    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->output_min = out_min;
    pid->output_max = out_max;
}

float PID_Update(PID_t *pid, float target, float current)
{
    if (pid == 0)
    {
        return 0.0f;
    }

    float error = target - current;
    pid->integral += error;
    if (pid->ki > 0.0f)
    {
        float integral_limit_max = pid->output_max / pid->ki;
        float integral_limit_min = pid->output_min / pid->ki;
        pid->integral = clampf(pid->integral, integral_limit_min, integral_limit_max);
    }
    float derivative = error - pid->prev_error;
    pid->prev_error = error;

    float output = (pid->kp * error) + (pid->ki * pid->integral) + (pid->kd * derivative);
    return clampf(output, pid->output_min, pid->output_max);
}

void PID_Reset(PID_t *pid)
{
    if (pid == 0)
    {
        return;
    }

    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
}

