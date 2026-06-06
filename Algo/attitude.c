#include "Algo/attitude.h"

static Attitude_t s_attitude = {0.0f, 0.0f};

void Attitude_Init(void)
{
    s_attitude.pitch = 0.0f;
    s_attitude.roll = 0.0f;
}

void Attitude_Update(float ax, float ay, float az, float gx, float gy, float gz, float dt)
{
    (void)ax;
    (void)ay;
    (void)az;
    (void)gx;
    (void)gy;
    (void)gz;
    (void)dt;
}

Attitude_t Attitude_Get(void)
{
    return s_attitude;
}

float Attitude_GetPitch(void)
{
    return s_attitude.pitch;
}

float Attitude_GetRoll(void)
{
    return s_attitude.roll;
}

