#pragma once

typedef struct
{
    float pitch;
    float roll;
} Attitude_t;

void Attitude_Init(void);
void Attitude_Update(float ax, float ay, float az, float gx, float gy, float gz, float dt);
Attitude_t Attitude_Get(void);
float Attitude_GetPitch(void);
float Attitude_GetRoll(void);

