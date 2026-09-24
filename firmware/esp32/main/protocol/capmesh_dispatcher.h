#pragma once

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#define CAPMESH_PROTOCOL_VERSION "capmesh/0.1"
#define CAPMESH_DEFAULT_SECRET "capmesh-secret-key-2026"

/**
 * Initialize the CapMesh capability dispatcher.
 * 
 * @param device_id Unique ID of this provider (e.g. "esp32-c6-96a0").
 */
esp_err_t capmesh_dispatcher_init(const char *device_id);

/**
 * Get the static or dynamic manifest JSON representation.
 * 
 * @param[out] buf Buffer to store manifest JSON string.
 * @param max_len Maximum length of buffer.
 * @return Length of manifest JSON, or -1 on error.
 */
int capmesh_dispatcher_get_manifest(char *buf, size_t max_len);

/**
 * Process an incoming capability invocation request.
 * Completely transport-agnostic: input is raw JSON, output is receipt JSON.
 * 
 * @param request_json Null-terminated JSON string of invocation request.
 * @param[out] response_buf Buffer to store receipt/error JSON string.
 * @param max_len Maximum length of response buffer.
 * @return Length of response JSON, or -1 on error.
 */
int capmesh_dispatcher_handle_request(const char *request_json, char *response_buf, size_t max_len);

/**
 * Enable or disable strict HMAC authorization verification (Phase 3).
 * When disabled (Phase 1-2), mock authorization ("mock" or empty) is accepted.
 */
void capmesh_dispatcher_set_auth_required(bool required);
