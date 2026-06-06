#include "Algo/filter.h"

float Filter_Clamp(float value, float min_value, float max_value)
{
    if (value < min_value)
    {
        return min_value;
    }
    if (value > max_value)
    {
        return max_value;
    }
    return value;
}

float Filter_AlphaBlend(float prev, float current, float alpha)
{
    return (1.0f - alpha) * prev + alpha * current;
}

