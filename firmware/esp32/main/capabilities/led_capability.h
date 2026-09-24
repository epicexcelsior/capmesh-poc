#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#define CAPMESH_LED_GPIO 8

/**
 * Initialize the onboard LED GPIO.
 */
esp_err_t led_capability_init(void);

/**
 * Execute the led.blink capability.
 * 
 * @param duration_s Total duration in seconds.
 * @param count Number of blink cycles.
 * @param[out] blinks_completed Actual blinks performed.
 * @return ESP_OK on success.
 */
esp_err_t led_capability_blink(int duration_s, int count, int *blinks_completed);
