#include "capabilities/led_capability.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "CAP_LED";

esp_err_t led_capability_init(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << CAPMESH_LED_GPIO),
        .mode = GPIO_MODE_INPUT_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&io_conf);
    if (err == ESP_OK) {
        gpio_set_level(CAPMESH_LED_GPIO, 0);
        ESP_LOGI(TAG, "LED capability initialized on GPIO %d (Input/Output pad readback enabled)", CAPMESH_LED_GPIO);
    }
    return err;
}

esp_err_t led_capability_blink(int duration_s, int count, int *blinks_completed, led_delivery_proof_t *proof)
{
    if (duration_s <= 0) {
        duration_s = 3;
    }
    if (count <= 0) {
        count = 5;
    }

    ESP_LOGI(TAG, "Executing led.blink: duration=%ds, count=%d with hardware pad verification", duration_s, count);

    int cycle_ms = (duration_s * 1000) / count;
    if (cycle_ms < 60) {
        cycle_ms = 60;
    }
    int on_ms = cycle_ms / 2;
    int off_ms = cycle_ms - on_ms;

    int done = 0;
    int verified_samples = 0;

    for (int i = 0; i < count; i++) {
        // Drive High
        gpio_set_level(CAPMESH_LED_GPIO, 1);
        vTaskDelay(pdMS_TO_TICKS(10));
        int high_readback = gpio_get_level(CAPMESH_LED_GPIO);

        int remain_on = on_ms > 10 ? (on_ms - 10) : 1;
        vTaskDelay(pdMS_TO_TICKS(remain_on));

        // Drive Low
        gpio_set_level(CAPMESH_LED_GPIO, 0);
        vTaskDelay(pdMS_TO_TICKS(10));
        int low_readback = gpio_get_level(CAPMESH_LED_GPIO);

        int remain_off = off_ms > 10 ? (off_ms - 10) : 1;
        vTaskDelay(pdMS_TO_TICKS(remain_off));

        done++;
        if (high_readback == 1 && low_readback == 0) {
            verified_samples++;
        }
    }

    if (blinks_completed) {
        *blinks_completed = done;
    }

    if (proof) {
        proof->observer_id = "esp32_gpio8_hw_pad";
        proof->expected_state = "PULSED";
        proof->observed_state = (verified_samples == done) ? "ACTIVE_HIGH" : "DEGRADED";
        proof->verified_samples = verified_samples;
        proof->total_samples = done;
        proof->readback_verified = (verified_samples == done);
        ESP_LOGI(TAG, "Physical delivery proof: %d/%d cycles verified by hardware pad readback (status=%s)",
                 verified_samples, done, proof->readback_verified ? "PASSED" : "FAILED");
    }

    ESP_LOGI(TAG, "led.blink finished: %d blinks performed", done);
    return ESP_OK;
}
