#include "Services/control_service.h"

static PID_t s_angle_pid;

void ControlService_Init(void)
{
    PID_Init(&s_angle_pid, 1.0f, 0.0f, 0.0f, -100.0f, 100.0f);
}

float ControlService_UpdateAngle(float target_angle, float current_angle)
{
    return PID_Update(&s_angle_pid, target_angle, current_angle);
}

