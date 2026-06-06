#include "App/app.h"

#include "BSP/bsp_board.h"
#include "BSP/bsp_uart_log.h"
#include "Services/sensor_service.h"
#include "Services/system_service.h"
#include "Config/device_config.h"

void App_Init(void)
{
    BSP_Board_Init();
    BSP_Log_Init();
    SensorService_Init();
    SystemService_Init();
}

void App_Loop(void)
{
    SensorData_t data = SensorService_GetData();
    LOG_INFO("pitch=%.2f roll=%.2f temp=%.2f dist=%.2f",
             data.pitch, data.roll, data.temperature_c, data.distance_cm);
    BSP_DelayMs(APP_LOOP_PERIOD_MS);
}

