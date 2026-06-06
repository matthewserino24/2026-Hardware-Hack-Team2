#pragma once

#include "Algo/pid.h"

void ControlService_Init(void);
float ControlService_UpdateAngle(float target_angle, float current_angle);

