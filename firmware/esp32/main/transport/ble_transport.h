#pragma once

#include "esp_err.h"

/**
 * Initialize the BLE transport using Apache NimBLE.
 * Configures the GATT server with CapMesh Service and characteristics,
 * and begins advertising.
 * 
 * @param device_name The BLE GAP advertised name (e.g. "capmesh-96a0").
 * @return ESP_OK on success.
 */
esp_err_t capmesh_ble_transport_init(const char *device_name);
