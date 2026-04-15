#pragma once

#include "esp_err.h"
#include "esp_camera.h"

esp_err_t camera_setup();

esp_err_t camera_capture(void (*process_image)(camera_fb_t *fb));