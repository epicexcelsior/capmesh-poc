#include "protocol/capmesh_dispatcher.h"
#include "capabilities/led_capability.h"
#include "capabilities/contact_capability.h"
#include "cJSON.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

static const char *TAG = "DISPATCHER";

static char s_device_id[64] = "esp32-c6-unknown";
static bool s_auth_required = false;
static int64_t s_epoch_offset_s = 0;
static SemaphoreHandle_t s_dispatch_lock;

// Simple replay prevention table
#define REPLAY_WINDOW_SIZE 64
static uint32_t s_seen_nonces[REPLAY_WINDOW_SIZE] = {0};
static uint32_t s_nonce_expirations[REPLAY_WINDOW_SIZE] = {0};

static bool is_nonce_seen(uint32_t nonce)
{
    if (nonce == 0) {
        return false;
    }
    for (size_t i = 0; i < REPLAY_WINDOW_SIZE; i++) {
        if (s_seen_nonces[i] == nonce) {
            return true;
        }
    }
    return false;
}

static bool record_nonce(uint32_t nonce, uint32_t expiration, uint32_t now)
{
    for (size_t i = 0; i < REPLAY_WINDOW_SIZE; i++) {
        if (s_seen_nonces[i] == 0 || s_nonce_expirations[i] < now) {
            s_seen_nonces[i] = nonce;
            s_nonce_expirations[i] = expiration;
            return true;
        }
    }
    return false;
}

esp_err_t capmesh_dispatcher_init(const char *device_id)
{
    if (device_id && strlen(device_id) > 0) {
        strncpy(s_device_id, device_id, sizeof(s_device_id) - 1);
        s_device_id[sizeof(s_device_id) - 1] = '\0';
    }
    memset(s_seen_nonces, 0, sizeof(s_seen_nonces));
    memset(s_nonce_expirations, 0, sizeof(s_nonce_expirations));
    s_epoch_offset_s = 0;
    s_dispatch_lock = xSemaphoreCreateMutex();
    if (!s_dispatch_lock) return ESP_ERR_NO_MEM;
    ESP_LOGI(TAG, "Dispatcher initialized for device: %s (auth_required=%d)", s_device_id, s_auth_required);
    return ESP_OK;
}

void capmesh_dispatcher_set_auth_required(bool required)
{
    s_auth_required = required;
    ESP_LOGI(TAG, "Strict authorization requirement set to: %d", required);
}

int capmesh_dispatcher_get_manifest(char *buf, size_t max_len)
{
    if (!buf || max_len == 0) {
        return -1;
    }

    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "protocol", CAPMESH_PROTOCOL_VERSION);
    cJSON_AddStringToObject(root, "device_id", s_device_id);

    cJSON *caps = cJSON_CreateArray();
    cJSON *cap = cJSON_CreateObject();
    cJSON_AddStringToObject(cap, "id", "led.blink");
    cJSON_AddStringToObject(cap, "description", "Blink onboard status LED");

    cJSON *pricing = cJSON_CreateObject();
    cJSON_AddStringToObject(pricing, "model", "fixed");
    cJSON_AddStringToObject(pricing, "amount", "0.001");
    cJSON_AddStringToObject(pricing, "currency", "mock-usdc");
    cJSON_AddItemToObject(cap, "pricing", pricing);

    cJSON_AddItemToArray(caps, cap);
    cJSON *observe = cJSON_CreateObject();
    cJSON_AddStringToObject(observe, "id", "state.observe");
    cJSON_AddStringToObject(observe, "description", "Fresh GPIO9 contact at demo-gate (BOOT button stand-in)");
    cJSON *observe_price = cJSON_CreateObject();
    cJSON_AddStringToObject(observe_price, "model", "fixed");
    cJSON_AddStringToObject(observe_price, "amount", "0.001");
    cJSON_AddStringToObject(observe_price, "currency", "mock-usdc");
    cJSON_AddItemToObject(observe, "pricing", observe_price);
    cJSON_AddItemToArray(caps, observe);
    cJSON_AddItemToObject(root, "capabilities", caps);

    char *json_str = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);

    if (!json_str) {
        return -1;
    }

    size_t len = strlen(json_str);
    if (len >= max_len) {
        free(json_str);
        return -1;
    }

    strncpy(buf, json_str, max_len);
    free(json_str);
    return (int)len;
}

#include <inttypes.h>

// --- Self-contained RFC 6234 SHA-256 & RFC 2104 HMAC-SHA-256 ---
#define SHA256_ROTR(a,b) (((a) >> (b)) | ((a) << (32 - (b))))
#define SHA256_CH(x,y,z) (((x) & (y)) ^ (~(x) & (z)))
#define SHA256_MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define SHA256_EP0(x) (SHA256_ROTR(x,2) ^ SHA256_ROTR(x,13) ^ SHA256_ROTR(x,22))
#define SHA256_EP1(x) (SHA256_ROTR(x,6) ^ SHA256_ROTR(x,11) ^ SHA256_ROTR(x,25))
#define SHA256_SIG0(x) (SHA256_ROTR(x,7) ^ SHA256_ROTR(x,18) ^ ((x) >> 3))
#define SHA256_SIG1(x) (SHA256_ROTR(x,17) ^ SHA256_ROTR(x,19) ^ ((x) >> 10))

static const uint32_t K256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

typedef struct {
    uint8_t data[64];
    uint32_t datalen;
    uint64_t bitlen;
    uint32_t state[8];
} sha256_ctx_t;

static void sha256_transform(sha256_ctx_t *ctx, const uint8_t data[])
{
    uint32_t a, b, c, d, e, f, g, h, i, j, t1, t2, m[64];
    for (i = 0, j = 0; i < 16; ++i, j += 4)
        m[i] = ((uint32_t)data[j] << 24) | ((uint32_t)data[j + 1] << 16) | ((uint32_t)data[j + 2] << 8) | data[j + 3];
    for (; i < 64; ++i)
        m[i] = SHA256_SIG1(m[i - 2]) + m[i - 7] + SHA256_SIG0(m[i - 15]) + m[i - 16];

    a = ctx->state[0]; b = ctx->state[1]; c = ctx->state[2]; d = ctx->state[3];
    e = ctx->state[4]; f = ctx->state[5]; g = ctx->state[6]; h = ctx->state[7];

    for (i = 0; i < 64; ++i) {
        t1 = h + SHA256_EP1(e) + SHA256_CH(e,f,g) + K256[i] + m[i];
        t2 = SHA256_EP0(a) + SHA256_MAJ(a,b,c);
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }

    ctx->state[0] += a; ctx->state[1] += b; ctx->state[2] += c; ctx->state[3] += d;
    ctx->state[4] += e; ctx->state[5] += f; ctx->state[6] += g; ctx->state[7] += h;
}

static void sha256_init_ctx(sha256_ctx_t *ctx)
{
    ctx->datalen = 0;
    ctx->bitlen = 0;
    ctx->state[0] = 0x6a09e667; ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372; ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f; ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab; ctx->state[7] = 0x5be0cd19;
}

static void sha256_update(sha256_ctx_t *ctx, const uint8_t data[], size_t len)
{
    for (size_t i = 0; i < len; ++i) {
        ctx->data[ctx->datalen] = data[i];
        ctx->datalen++;
        if (ctx->datalen == 64) {
            sha256_transform(ctx, ctx->data);
            ctx->bitlen += 512;
            ctx->datalen = 0;
        }
    }
}

static void sha256_final(sha256_ctx_t *ctx, uint8_t hash[])
{
    uint32_t i = ctx->datalen;
    if (ctx->datalen < 56) {
        ctx->data[i++] = 0x80;
        while (i < 56) ctx->data[i++] = 0x00;
    } else {
        ctx->data[i++] = 0x80;
        while (i < 64) ctx->data[i++] = 0x00;
        sha256_transform(ctx, ctx->data);
        memset(ctx->data, 0, 56);
    }
    ctx->bitlen += ctx->datalen * 8;
    ctx->data[63] = ctx->bitlen;
    ctx->data[62] = ctx->bitlen >> 8;
    ctx->data[61] = ctx->bitlen >> 16;
    ctx->data[60] = ctx->bitlen >> 24;
    ctx->data[59] = ctx->bitlen >> 32;
    ctx->data[58] = ctx->bitlen >> 40;
    ctx->data[57] = ctx->bitlen >> 48;
    ctx->data[56] = ctx->bitlen >> 56;
    sha256_transform(ctx, ctx->data);

    for (i = 0; i < 4; ++i) {
        hash[i]      = (ctx->state[0] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 4]  = (ctx->state[1] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 8]  = (ctx->state[2] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 12] = (ctx->state[3] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 16] = (ctx->state[4] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 20] = (ctx->state[5] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 24] = (ctx->state[6] >> (24 - i * 8)) & 0x000000ff;
        hash[i + 28] = (ctx->state[7] >> (24 - i * 8)) & 0x000000ff;
    }
}

static void sha256_compute(const uint8_t *data, size_t len, uint8_t hash[32])
{
    sha256_ctx_t ctx;
    sha256_init_ctx(&ctx);
    sha256_update(&ctx, data, len);
    sha256_final(&ctx, hash);
}

static bool compute_hmac_sha256(const char *key, const char *msg, uint8_t output[32])
{
    uint8_t k_pad[64];
    uint8_t tk[32];
    size_t key_len = strlen(key);

    if (key_len > 64) {
        sha256_compute((const uint8_t *)key, key_len, tk);
        key = (const char *)tk;
        key_len = 32;
    }

    // Inner hash: H( (K ^ 0x36) || msg )
    sha256_ctx_t ctx;
    sha256_init_ctx(&ctx);
    memset(k_pad, 0x36, sizeof(k_pad));
    for (size_t i = 0; i < key_len; i++) {
        k_pad[i] ^= (uint8_t)key[i];
    }
    sha256_update(&ctx, k_pad, 64);
    sha256_update(&ctx, (const uint8_t *)msg, strlen(msg));
    uint8_t inner_hash[32];
    sha256_final(&ctx, inner_hash);

    // Outer hash: H( (K ^ 0x5c) || inner_hash )
    sha256_init_ctx(&ctx);
    memset(k_pad, 0x5c, sizeof(k_pad));
    for (size_t i = 0; i < key_len; i++) {
        k_pad[i] ^= (uint8_t)key[i];
    }
    sha256_update(&ctx, k_pad, 64);
    sha256_update(&ctx, inner_hash, 32);
    sha256_final(&ctx, output);

    return true;
}

static bool verify_hmac(const char *message, const char *hex_digest)
{
    uint8_t hmac_out[32];
    if (!compute_hmac_sha256(CAPMESH_DEFAULT_SECRET, message, hmac_out)) {
        return false;
    }

    char expected_hex[65];
    for (int i = 0; i < 32; i++) {
        sprintf(&expected_hex[i * 2], "%02x", hmac_out[i]);
    }
    expected_hex[64] = '\0';

    if (strlen(hex_digest) != 64) return false;
    unsigned char difference = 0;
    for (int i = 0; i < 64; i++) difference |= expected_hex[i] ^ hex_digest[i];
    return difference == 0;
}

static int format_error_response(const char *req_id, const char *code, const char *message, char *response_buf, size_t max_len)
{
    cJSON *err = cJSON_CreateObject();
    cJSON_AddStringToObject(err, "protocol", CAPMESH_PROTOCOL_VERSION);
    cJSON_AddStringToObject(err, "request_id", req_id ? req_id : "req-unknown");
    cJSON_AddStringToObject(err, "status", "error");
    cJSON *eobj = cJSON_CreateObject();
    cJSON_AddStringToObject(eobj, "code", code);
    cJSON_AddStringToObject(eobj, "message", message);
    cJSON_AddItemToObject(err, "error", eobj);
    char *str = cJSON_PrintUnformatted(err);
    cJSON_Delete(err);
    int len = snprintf(response_buf, max_len, "%s", str ? str : "{}");
    free(str);
    ESP_LOGW(TAG, "Generated error receipt [%s]: %s", code, response_buf);
    return len;
}

static bool is_uint(cJSON *item, uint32_t maximum)
{
    return cJSON_IsNumber(item) && item->valuedouble >= 0 &&
           item->valuedouble <= maximum && floor(item->valuedouble) == item->valuedouble;
}

static int observation_receipt(const char *req_id, uint32_t nonce, uint32_t start,
                               char *buf, size_t max_len)
{
    bool closed;
    int stable;
    contact_capability_sample(&closed, &stable);
    uint32_t end = (uint32_t)(s_epoch_offset_s + esp_timer_get_time() / 1000000ULL);
    cJSON *receipt = cJSON_CreateObject();
    cJSON_AddStringToObject(receipt, "protocol", CAPMESH_PROTOCOL_VERSION);
    cJSON_AddStringToObject(receipt, "request_id", req_id);
    cJSON_AddStringToObject(receipt, "status", "success");
    cJSON_AddStringToObject(receipt, "provider", s_device_id);
    cJSON_AddStringToObject(receipt, "capability", "state.observe");
    cJSON_AddNumberToObject(receipt, "nonce", nonce);
    cJSON *params = cJSON_CreateObject();
    cJSON_AddStringToObject(params, "location", "demo-gate");
    cJSON_AddItemToObject(receipt, "parameters", params);
    cJSON *result = cJSON_CreateObject();
    cJSON_AddStringToObject(result, "metric", "gate.closed");
    cJSON_AddStringToObject(result, "sensor", "gpio9-contact");
    cJSON_AddBoolToObject(result, "closed", closed);
    cJSON_AddNumberToObject(result, "stable_samples", stable);
    cJSON_AddNumberToObject(result, "total_samples", FIELDPROOF_CONTACT_SAMPLES);
    cJSON_AddItemToObject(receipt, "result", result);
    cJSON_AddNumberToObject(receipt, "started_at", start);
    cJSON_AddNumberToObject(receipt, "completed_at", end);
    char message[384];
    snprintf(message, sizeof(message),
             "fieldproof-observation-v1|%s|%s|%s|state.observe|demo-gate|%" PRIu32 "|gate.closed|gpio9-contact|%d|%d|%d|%" PRIu32 "|%" PRIu32,
             CAPMESH_PROTOCOL_VERSION, req_id, s_device_id, nonce, closed ? 1 : 0,
             stable, FIELDPROOF_CONTACT_SAMPLES, start, end);
    uint8_t digest[32];
    compute_hmac_sha256(CAPMESH_DEFAULT_SECRET, message, digest);
    char signature[69] = "v2:";
    for (int i = 0; i < 32; i++) sprintf(signature + 3 + i * 2, "%02x", digest[i]);
    cJSON_AddStringToObject(receipt, "receipt_signature", signature);
    char *json = cJSON_PrintUnformatted(receipt);
    cJSON_Delete(receipt);
    if (!json) return -1;
    int len = snprintf(buf, max_len, "%s", json);
    free(json);
    if (len < 0 || (size_t)len >= max_len || len > 512)
        return format_error_response(req_id, "RECEIPT_TOO_LARGE", "Receipt exceeds BLE size", buf, max_len);
    return len;
}

static int handle_request_locked(const char *request_json, char *response_buf, size_t max_len)
{
    if (!request_json || !response_buf || max_len == 0) {
        return -1;
    }

    cJSON *req = cJSON_Parse(request_json);
    if (!req) {
        return format_error_response("req-unknown", "JSON_PARSE_ERROR", "Failed to parse request JSON", response_buf, max_len);
    }

    cJSON *proto_item = cJSON_GetObjectItem(req, "protocol");
    cJSON *req_id_item = cJSON_GetObjectItem(req, "request_id");
    cJSON *cap_item = cJSON_GetObjectItem(req, "capability");
    cJSON *nonce_item = cJSON_GetObjectItem(req, "nonce");
    cJSON *exp_item = cJSON_GetObjectItem(req, "expiration");
    cJSON *auth_item = cJSON_GetObjectItem(req, "authorization");
    cJSON *params_item = cJSON_GetObjectItem(req, "parameters");

    char req_id[64] = "req-unknown";
    char cap_id[32] = "";
    if (req_id_item && cJSON_IsString(req_id_item) && req_id_item->valuestring) {
        strncpy(req_id, req_id_item->valuestring, sizeof(req_id) - 1);
        req_id[sizeof(req_id) - 1] = '\0';
    }
    if (cap_item && cJSON_IsString(cap_item) && cap_item->valuestring) {
        strncpy(cap_id, cap_item->valuestring, sizeof(cap_id) - 1);
        cap_id[sizeof(cap_id) - 1] = '\0';
    }

    uint32_t nonce = is_uint(nonce_item, 0x7fffffff) ? (uint32_t)nonce_item->valuedouble : 0;
    uint32_t exp = is_uint(exp_item, UINT32_MAX) ? (uint32_t)exp_item->valuedouble : 0;
    cJSON *device_item = cJSON_GetObjectItem(req, "device_id");
    cJSON *ts_item = cJSON_GetObjectItem(req, "timestamp");
    uint32_t req_ts = is_uint(ts_item, UINT32_MAX - 300) ? (uint32_t)ts_item->valuedouble : 0;
    bool observing = strcmp(cap_id, "state.observe") == 0;

    int duration = 3;
    int count = 5;
    if (params_item && cJSON_IsObject(params_item)) {
        cJSON *dur_item = cJSON_GetObjectItem(params_item, "duration");
        cJSON *cnt_item = cJSON_GetObjectItem(params_item, "count");
        if (dur_item && cJSON_IsNumber(dur_item)) {
            duration = dur_item->valueint;
        }
        if (cnt_item && cJSON_IsNumber(cnt_item)) {
            count = cnt_item->valueint;
        }
    }

    // 1. Validate Protocol
    if (!proto_item || !cJSON_IsString(proto_item) || strcmp(proto_item->valuestring, CAPMESH_PROTOCOL_VERSION) != 0) {
        cJSON_Delete(req);
        return format_error_response(req_id, "INVALID_PROTOCOL", "Unsupported protocol version", response_buf, max_len);
    }

    // 2. Validate Capability
    if (strcmp(cap_id, "led.blink") != 0 && !observing) {
        cJSON_Delete(req);
        return format_error_response(req_id, "UNKNOWN_CAPABILITY", "Requested capability is not offered by provider", response_buf, max_len);
    }

    if (exp > 0 && exp <= req_ts) {
        cJSON_Delete(req);
        return format_error_response(req_id, "AUTH_EXPIRED", "Request expiration is not after its timestamp", response_buf, max_len);
    }

    if (!req_id_item || !cJSON_IsString(req_id_item) || !strlen(req_id) || strlen(req_id_item->valuestring) > 16 ||
        strspn(req_id, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_") != strlen(req_id) ||
        !device_item || !cJSON_IsString(device_item) || strcmp(device_item->valuestring, s_device_id) != 0 ||
        nonce == 0 || req_ts < 1700000000U || exp <= req_ts || exp - req_ts > 300U ||
        !params_item || !cJSON_IsObject(params_item) ||
        (!observing && (!is_uint(cJSON_GetObjectItem(params_item, "duration"), 10) ||
                        !is_uint(cJSON_GetObjectItem(params_item, "count"), 100)))) {
        cJSON_Delete(req);
        return format_error_response(req_id, "INVALID_REQUEST", "Missing or invalid signed request fields", response_buf, max_len);
    }

    if (observing) {
        cJSON *location = cJSON_GetObjectItem(params_item, "location");
        if (!cJSON_IsString(location) || strcmp(location->valuestring, "demo-gate") != 0 ||
            cJSON_GetArraySize(params_item) != 1) {
            cJSON_Delete(req);
            return format_error_response(req_id, "INVALID_PARAMETERS", "Only demo-gate is provisioned", response_buf, max_len);
        }
    }

    // 3. Replay Protection (Nonce check)
    if (nonce > 0 && is_nonce_seen(nonce)) {
        ESP_LOGW(TAG, "Replay rejected for nonce: %" PRIu32, nonce);
        cJSON_Delete(req);
        return format_error_response(req_id, "REPLAY_DETECTED", "Nonce has already been processed", response_buf, max_len);
    }

    // 4. Expiration check (if expiration is specified)
    uint32_t uptime_s = (uint32_t)(esp_timer_get_time() / 1000000ULL);
    uint32_t now_s = (s_epoch_offset_s > 0) ? (uint32_t)(s_epoch_offset_s + uptime_s) : req_ts;
    if (exp < now_s || (s_epoch_offset_s > 0 && (req_ts + 30U < now_s || req_ts > now_s + 30U))) {
        ESP_LOGW(TAG, "Request expired: exp=%" PRIu32 ", now=%" PRIu32, exp, now_s);
        cJSON_Delete(req);
        return format_error_response(req_id, "AUTH_EXPIRED", "Request expiration timestamp is in the past", response_buf, max_len);
    }

    // 5. Authorization Verification
    if (s_auth_required) {
        bool auth_valid = false;
        if (auth_item && cJSON_IsObject(auth_item)) {
            cJSON *type_item = cJSON_GetObjectItem(auth_item, "type");
            cJSON *token_item = cJSON_GetObjectItem(auth_item, "token");
            if (type_item && token_item && cJSON_IsString(type_item) && cJSON_IsString(token_item)) {
                if (strcmp(type_item->valuestring, "hmac-sha256-v2") == 0) {
                    char msg[256];
                    if (observing) {
                        snprintf(msg, sizeof(msg), "fieldproof-auth-v1|%s|%s|state.observe|demo-gate|%" PRIu32 "|%" PRIu32 "|%" PRIu32,
                                 req_id, s_device_id, nonce, req_ts, exp);
                    } else {
                        snprintf(msg, sizeof(msg), "capmesh-auth-v2|%s|%s|%s|%d|%d|%" PRIu32 "|%" PRIu32 "|%" PRIu32,
                             req_id, s_device_id, cap_id, duration, count, nonce, req_ts, exp);
                    }
                    auth_valid = verify_hmac(msg, token_item->valuestring);
                }
            }
        }

        if (!auth_valid) {
            ESP_LOGW(TAG, "Authorization check failed for request: %s", req_id);
            cJSON_Delete(req);
            return format_error_response(req_id, "UNAUTHORIZED", "Invalid or missing cryptographic authorization signature", response_buf, max_len);
        }
    }

    if (!observing && (duration < 1 || duration > 10 || count < 1 || count > 10 || count > duration * 10)) {
        cJSON_Delete(req);
        return format_error_response(req_id, "INVALID_PARAMETERS", "Blink duration or count is outside demo limits", response_buf, max_len);
    }

    if (s_epoch_offset_s == 0) {
        s_epoch_offset_s = (int64_t)req_ts - (int64_t)uptime_s;
        ESP_LOGI(TAG, "Epoch set from authenticated request: %" PRIu32, req_ts);
    }

    // Record valid nonce
    if (!record_nonce(nonce, exp, now_s)) {
        cJSON_Delete(req);
        return format_error_response(req_id, "NONCE_CACHE_FULL", "Retry after existing authorizations expire", response_buf, max_len);
    }

    if (observing) {
        cJSON_Delete(req);
        return observation_receipt(req_id, nonce, now_s, response_buf, max_len);
    }

    // 6. Execute Capability (Led blink with independent hardware readback)
    uint32_t start_time = now_s;
    int blinks_done = 0;
    led_delivery_proof_t proof = {0};
    led_capability_blink(duration, count, &blinks_done, &proof);
    uint32_t end_time = (s_epoch_offset_s > 0) ? (uint32_t)(s_epoch_offset_s + (esp_timer_get_time() / 1000000ULL)) : (uint32_t)(esp_timer_get_time() / 1000000ULL);

    // 7. Formulate Receipt JSON
    cJSON *receipt = cJSON_CreateObject();
    cJSON_AddStringToObject(receipt, "protocol", CAPMESH_PROTOCOL_VERSION);
    cJSON_AddStringToObject(receipt, "request_id", req_id);
    cJSON_AddStringToObject(receipt, "status", "success");
    cJSON_AddStringToObject(receipt, "provider", s_device_id);
    cJSON_AddStringToObject(receipt, "capability", cap_id);

    cJSON *r_params = cJSON_CreateObject();
    cJSON_AddNumberToObject(r_params, "duration", duration);
    cJSON_AddNumberToObject(r_params, "count", count);
    cJSON_AddItemToObject(receipt, "parameters", r_params);

    cJSON *result = cJSON_CreateObject();
    cJSON_AddNumberToObject(result, "blinks_completed", blinks_done);
    cJSON_AddItemToObject(receipt, "result", result);

    // 8. Attach Physical Delivery Proof (Solving the Actuator Oracle Problem)
    cJSON *dp = cJSON_CreateObject();
    cJSON_AddStringToObject(dp, "observer_id", proof.observer_id ? proof.observer_id : "esp32_gpio8_hw_pad");
    cJSON_AddStringToObject(dp, "expected_state", proof.expected_state ? proof.expected_state : "PULSED");
    cJSON_AddStringToObject(dp, "observed_state", proof.observed_state ? proof.observed_state : "ACTIVE_HIGH");
    cJSON_AddNumberToObject(dp, "verified_samples", proof.verified_samples);
    cJSON_AddNumberToObject(dp, "total_samples", proof.total_samples);
    cJSON_AddBoolToObject(dp, "readback_verified", proof.readback_verified);
    cJSON_AddItemToObject(receipt, "delivery_proof", dp);

    cJSON_AddNumberToObject(receipt, "started_at", start_time);
    cJSON_AddNumberToObject(receipt, "completed_at", end_time);

    // Generate receipt signature / authenticator
    char receipt_msg[256];
    snprintf(receipt_msg, sizeof(receipt_msg),
             "capmesh-receipt-v2|%s|%s|%s|%d|%d|%d|%s|%s|%s|%d|%d|%d|%" PRIu32 "|%" PRIu32,
             req_id, s_device_id, cap_id, duration, count, blinks_done,
             proof.observer_id, proof.expected_state, proof.observed_state,
             proof.verified_samples, proof.total_samples, proof.readback_verified ? 1 : 0,
             start_time, end_time);
    uint8_t hmac_out[32];
    char sig_hex[65] = "mock-sig";
    if (compute_hmac_sha256(CAPMESH_DEFAULT_SECRET, receipt_msg, hmac_out)) {
        for (int i = 0; i < 32; i++) {
            sprintf(&sig_hex[i * 2], "%02x", hmac_out[i]);
        }
        sig_hex[64] = '\0';
    }
    char versioned_sig[69];
    snprintf(versioned_sig, sizeof(versioned_sig), "v2:%s", sig_hex);
    cJSON_AddStringToObject(receipt, "receipt_signature", versioned_sig);

    char *out_str = cJSON_PrintUnformatted(receipt);
    cJSON_Delete(receipt);
    cJSON_Delete(req);

    if (!out_str) {
        return -1;
    }

    int len = snprintf(response_buf, max_len, "%s", out_str);
    free(out_str);
    if (len < 0 || len >= max_len || len > 512) {
        return format_error_response(req_id, "RECEIPT_TOO_LARGE", "Receipt exceeds BLE characteristic size", response_buf, max_len);
    }
    ESP_LOGI(TAG, "Generated receipt: %s", response_buf);
    return len;
}

int capmesh_dispatcher_handle_request(const char *request_json, char *response_buf, size_t max_len)
{
    if (!s_dispatch_lock || xSemaphoreTake(s_dispatch_lock, pdMS_TO_TICKS(100)) != pdTRUE)
        return format_error_response("req-unknown", "BUSY", "Another request is in progress", response_buf, max_len);
    int result = handle_request_locked(request_json, response_buf, max_len);
    xSemaphoreGive(s_dispatch_lock);
    return result;
}
