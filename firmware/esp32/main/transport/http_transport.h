#pragma once

#include "esp_err.h"

/**
 * Initialize Wi-Fi SoftAP and start embedded HTTP server for CapMesh.
 * Exposes GET /manifest, POST /invoke, and GET /receipt.
 * 
 * @param ap_ssid SSID for the SoftAP network (e.g. "CAPMESH_96A2").
 * @return ESP_OK on success.
 */
esp_err_t capmesh_http_transport_init(const char *ap_ssid);
