#pragma once

typedef struct
{
    float pitch;
    float roll;
} AttitudeServiceData_t;

void AttitudeService_Init(void);
AttitudeServiceData_t AttitudeService_GetData(void);

