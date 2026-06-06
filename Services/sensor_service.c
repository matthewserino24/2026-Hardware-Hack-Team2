#include "Services/sensor_service.h"

#include "Algo/attitude.h"
#include "Drivers/Distance/hcsr04.h"
#include "Drivers/Temperature/mcp9808.h"
#include <math.h>

void SensorService_Init(void)
{
    Attitude_Init();
}

SensorData_t SensorService_GetData(void)
{
    SensorData_t data = {0.0f, 0.0f, 0.0f, 0.0f};

    if (MCP9808_ReadTemperature(&data.temperature_c) != STATUS_OK)
    {
        data.temperature_c = NAN;
    }

    if (HCSR04_ReadDistanceCm(&data.distance_cm) != STATUS_OK)
    {
        data.distance_cm = NAN;
    }

    data.pitch = Attitude_GetPitch();
    data.roll = Attitude_GetRoll();

    return data;
}

