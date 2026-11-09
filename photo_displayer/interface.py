import serial
from PIL import Image
import numpy as np
import os
from pathlib import Path
import threading
import pandas as pd
import time
import matplotlib.pyplot as plt
import cv2

ser = serial.Serial("/dev/ttyACM0", baudrate=115200)

START_CODE = 0x01
SEND_BYTES_CODE = 0x02
TAKE_PICTURE_CODE = 0x03
SEND_TEXT_CODE = 0x4
CODE_END = 0xff

image_folder_path = Path("/home/rsadr0pyz/Desktop/pad25/anonymous-images/")
esp_image_folder_path = Path("/home/rsadr0pyz/Desktop/pad25/esp-images/")
dataset_path = Path("/home/rsadr0pyz/Desktop/pad25/anonymous-metadata-full.csv")
reddit_path = Path("/home/rsadr0pyz/Desktop/reddit/reddit")
test_img = Image.open("/home/rsadr0pyz/Desktop/Untitled.jpeg")


#Configurado so para o reddit

# in_fold: da onde saem as images. out_fold: para onde vao as imagens novas.
dataset = pd.DataFrame({"img-id": os.listdir(reddit_path), "in_fold": reddit_path, "out_fold":Path("/home/rsadr0pyz/Desktop/reddit/esp_images/")})

#Configurado so para o pad
#dataset = pd.read_csv(dataset_path)[["img-id"]]
#dataset["img-id"] = dataset["img-id"] + ".png"
#dataset["in_fold"] = image_folder_path
#dataset["out_fold"] = esp_image_folder_path

# Para fazer ambos ao msm tempo (mudar o nome das variaveis)
#dataset = pd.concat([reddit_dataset, pad_dataset])


class LatestValue:
    def __init__(self):
        self.value = None
        self.lock = threading.Lock()

    def set(self, v):
        with self.lock:
            self.value = v

    def get(self):
        with self.lock:
            v = self.value
            self.value = None
            return v  

def read_int():
    return int.from_bytes(ser.read(4), byteorder="little")

def read_code():
    return ser.read(1)[0]

def receive_text():
    size = read_int()
    text = ser.read(size).decode(encoding="ASCII")
    print(text, end="")

def rgb565_to_rgb888(bytes):
    data = np.frombuffer(bytes, dtype=np.uint16)
    data = data.byteswap()

    b = ((data & 0x1F) << 3).astype(np.uint8)
    g = (((data >> 5) & 0x3F) << 2).astype(np.uint8)
    r = (((data >> 11) & 0x1F) << 3).astype(np.uint8)
    
    rgb = np.stack([r,g,b], axis=-1)
    rgb = rgb.reshape((240, 240, 3))
    return rgb

def receive_img():
    size = read_int()
    img_bytes = ser.read(size)
    img_raw = rgb565_to_rgb888(img_bytes)
    
    img = Image.fromarray(img_raw, "RGB")
    img = img.rotate(180)
    last_img.set(img)

def com_esp():
    ser.write([START_CODE])
    code = read_code()
    if code != START_CODE:
        print(f"COM ERROR {code}")
        print(flush=True)
        exit()

    print("COM START")
    while True:
        code = read_code()
        print(f"code {code}")
        if(code == SEND_BYTES_CODE):
            receive_img()
        elif(code == SEND_TEXT_CODE):
            receive_text()
        else:
            print(f"INVALID CODE")
            print(flush=True)
            exit()

        end = read_code()
        if(end != CODE_END):
            print(f"EXPECTED TERMINATION {end} {code}")
            print(flush=True)
            exit()

def show_frame(img):
    img.rotate(90)
    if not isinstance(img, np.ndarray):
        img = np.array(img)

    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imshow("stream", img)

    key = cv2.waitKey(50)
    return key == 114 # 'r'

cv2.namedWindow("stream", cv2.WINDOW_NORMAL)   
com_thread = threading.Thread(target=com_esp, daemon=True)
com_thread.start()
last_img = LatestValue()


def center_crop_to_ratio(img, target_ratio):
    width, height = img.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(target_ratio * height)
        offset = (width - new_width) // 2
        crop_box = (offset, 0, width - offset, height)
    else:
        new_height = int(width / target_ratio)
        offset = (height - new_height) // 2
        crop_box = (0, offset, width, height - offset)

    return img.crop(crop_box)

def main_loop():
    global test_img, last_img
    first_time = True

    show_frame(test_img)
    while input() != "go":
        show_frame(test_img)
        ser.write([TAKE_PICTURE_CODE])

        capture = last_img.get()
        while capture == None:
            capture = last_img.get()
        show_frame(capture)

    for index, row in dataset.iterrows():

        if not pd.notna(row["img-id"]):
            continue

        img = Image.open(row["in_fold"] / (row["img-id"]) )
        img = center_crop_to_ratio(img, 1)
        
        if(show_frame(img)):
            return True

        if first_time:
            input()
            first_time = False

        ser.write([TAKE_PICTURE_CODE])

        capture = last_img.get()
        while capture == None:
            time.sleep(0.01)
            capture = last_img.get()
        print("found")

        capture.save(row["out_fold"] / (row["img-id"]))
    return False

while(main_loop()):
    pass