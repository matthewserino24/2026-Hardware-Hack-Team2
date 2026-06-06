#include "Services/attitude_service.h"

#include "Algo/attitude.h"

void AttitudeService_Init(void)
{
    Attitude_Init();
}

AttitudeServiceData_t AttitudeService_GetData(void)
{
    AttitudeServiceData_t data;
    data.pitch = Attitude_GetPitch();
    data.roll = Attitude_GetRoll();
    return data;
}

