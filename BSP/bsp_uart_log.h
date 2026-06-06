#pragma once

#include <stdarg.h>

typedef enum
{
    LOG_LEVEL_INFO = 0,
    LOG_LEVEL_WARN = 1,
    LOG_LEVEL_ERROR = 2
} LogLevel_t;

void BSP_Log_Init(void);
void BSP_Log_Print(LogLevel_t level, const char *fmt, ...);

#define LOG_INFO(...)  BSP_Log_Print(LOG_LEVEL_INFO, __VA_ARGS__)
#define LOG_WARN(...)  BSP_Log_Print(LOG_LEVEL_WARN, __VA_ARGS__)
#define LOG_ERROR(...) BSP_Log_Print(LOG_LEVEL_ERROR, __VA_ARGS__)

