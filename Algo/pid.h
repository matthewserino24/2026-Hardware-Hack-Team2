#pragma once

typedef struct
{
    float kp;
    float ki;
    float kd;
    float integral;
    float prev_error;
    float output_min;
    float output_max;
} PID_t;

void PID_Init(PID_t *pid, float kp, float ki, float kd, float out_min, float out_max);
float PID_Update(PID_t *pid, float target, float current);
void PID_Reset(PID_t *pid);

