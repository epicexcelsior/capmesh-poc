#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#define CAPMESH_LED_GPIO 8

typedef struct {
    const char *observer_id;
    const char *expected_state;
    const char *observed_state;
    int verified_samples;
    int total_samples;
    bool readback_verified;
} led_delivery_proof_t;

/**
 * Initialize the onboard LED GPIO.
 */
esp_err_t led_capability_init(void);

/**
 * Execute the led.blink capability with independent hardware readback.
 * 
 * @param duration_s Total duration in seconds.
 * @param count Number of blink cycles.
 * @param[out] blinks_completed Actual blinks performed.
 * @param[out] proof Independent hardware readback delivery proof.
 * @return ESP_OK on success.
 */
esp_err_t led_capability_blink(int duration_s, int count, int *blinks_completed, led_delivery_proof_t *proof);
