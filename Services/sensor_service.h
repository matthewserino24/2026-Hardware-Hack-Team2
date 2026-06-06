#pragma once

typedef struct
{
    float pitch;
    float roll;
    float temperature_c;
    float distance_cm;
} SensorData_t;

void SensorService_Init(void);
SensorData_t SensorService_GetData(void);

