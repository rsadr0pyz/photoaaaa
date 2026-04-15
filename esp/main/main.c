#include "tinyusb.h"
#include "tinyusb_cdc_acm.h"
#include <stdio.h>
#include "esp_log.h"
#include <stdarg.h>
#include "tinyusb_default_config.h"
#include <stdlib.h>
#include "camera/camera.h"

#define PORT TINYUSB_CDC_ACM_0
#define TAG "COM"

static const uint8_t START_CODE = 0x01;
static const uint8_t SEND_BYTES_CODE = 0x02;
static const uint8_t TAKE_PICTURE_CODE = 0x03;
static const uint8_t SEND_TEXT_PREFIX = 0x04;
static const uint8_t END_SUFIX = 0xff;

static const char SEND_TEXT_ERROR_MSG[] = "[ERROR] COULD NOT ALLOCATE BUFFER FOR SEND_TEXT()";
#define SEND_TEXT_ERROR_MSG_SIZE (sizeof(SEND_TEXT_ERROR_MSG) - 1)
static int connected = 0;

static void _write_data(const uint8_t* buf, int size);

static inline void send_code(uint8_t code)
{
    _write_data((uint8_t *)&code, 1);
}

void send_text(const char *fmt, ...)
{
    send_code(SEND_TEXT_PREFIX);

    va_list args;
    char *buf;
    va_start(args, fmt);
    int rc = vasprintf(&buf, fmt, args);
    va_end(args);

    int must_free = 1;
    const char *out = buf;
    if(rc == -1)
    {
        rc = SEND_TEXT_ERROR_MSG_SIZE;
        out = SEND_TEXT_ERROR_MSG;
        must_free = 0;
    }

    _write_data((uint8_t *)&rc, sizeof(int));
    _write_data((uint8_t *)out, rc);
    if(must_free) free(buf);

    send_code(END_SUFIX);
}

static void _write_data(const uint8_t* buf, int size)
{
    int sent = 0;
    while(sent != size)
    {
       sent += tinyusb_cdcacm_write_queue(PORT, buf+sent, size-sent);
       tinyusb_cdcacm_write_flush(PORT, 10);
       vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void send_bytes(const uint8_t* buf, int size)
{
    send_code(SEND_BYTES_CODE);
    _write_data((uint8_t *)&size, sizeof(int));
    _write_data(buf, size);
    send_code(END_SUFIX);
}

int is_connected()
{
    return connected;
}


void send_camera_data(camera_fb_t *fb)
{
    send_bytes(fb->buf, fb->len);
}


void read_bytes(uint8_t *buf, size_t amt)
{
    size_t total = 0;
    size_t len;
    while(total < amt)
    {
        tinyusb_cdcacm_read(TINYUSB_CDC_ACM_0,
                        buf+total,
                        amt-total,
                        &len);
        total += len;

        if (len > 0) 
            total += len;
        else 
            vTaskDelay(pdMS_TO_TICKS(1));
        
    }
    
}

void com_setup()
{

    ESP_LOGI(TAG, "USB initialization");
    const tinyusb_config_t tusb_cfg = TINYUSB_DEFAULT_CONFIG();
    ESP_ERROR_CHECK(tinyusb_driver_install(&tusb_cfg));

    tinyusb_config_cdcacm_t acm_cfg = {
        .cdc_port = TINYUSB_CDC_ACM_0,
        .callback_line_state_changed = NULL,
        .callback_rx = NULL,
        .callback_rx_wanted_char = NULL,
        .callback_line_coding_changed = NULL
    };


    ESP_ERROR_CHECK(tinyusb_cdcacm_init(&acm_cfg));

    //handshake
    uint8_t code = 0;
    read_bytes(&code, 1);
    if(code == START_CODE)
    {
        send_code(START_CODE);
        connected = true;
    }
    else
        send_text("INVALID CODE\n");
}

int app_main()
{
    com_setup();
    if(!connected) return 1;

    send_text("ESP START\n");
    while(1)
    {
        uint8_t code = 0;
        read_bytes(&code, 1);
        if(code == TAKE_PICTURE_CODE)
        {
            send_text("photo\n");
            if(camera_capture(send_camera_data) == ESP_FAIL)
                send_text("photo ERROR\n");
        }
        else
        {
            send_code(0x00);
        }
    }
   
    return 0;
}