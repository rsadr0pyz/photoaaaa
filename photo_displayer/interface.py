import serial
from PIL import Image
import numpy as np
import io
from pathlib import Path
import threading
import pandas as pd
import time
import matplotlib.pyplot as plt


ser = serial.Serial("/dev/ttyACM0")

START_CODE = 0x01
SEND_BYTES_CODE = 0x02
TAKE_PICTURE_CODE = 0x03
SEND_TEXT_CODE = 0x4
CODE_END = 0xff

image_folder_path = Path("/home/rsadr0pyz/Desktop/pad25/anonymous-images/")
esp_image_folder_path = Path("/home/rsadr0pyz/Desktop/pad25/esp-images/")
dataset_path = Path("/home/rsadr0pyz/Desktop/pad25/anonymous-metadata-full.csv")
dataset = pd.read_csv(dataset_path)

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


last_img = LatestValue()
stop = False    

def read_int():
    return int.from_bytes(ser.read(4), byteorder="little")

def read_code():
    return ser.read(1)[0]

def receive_text():
    size = read_int()
    text = ser.read(size).decode(encoding="ASCII")
    print(text, end="")


def receive_img():
    size = read_int()
    img_bytes = ser.read(size)
    img = Image.open(io.BytesIO(img_bytes))
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



def on_close(event):
    global com_thread, stop
    print("Figure closed!")
    exit()

plt.ion()
fig = plt.figure()
fig.canvas.mpl_connect('close_event', on_close)
ax = fig.add_subplot()
im = None

first_time = True

com_thread = threading.Thread(target=com_esp, daemon=True)
com_thread.start()

for index, row in dataset.iterrows():

    if not pd.notna(row["img-id"]):
        continue

    img = Image.open(image_folder_path / (row["img-id"]+".png") )
    
    if im == None:
        im = ax.imshow(img)
    else:
        im.set_data(img)

    plt.draw()       # Redraw the current figure
    plt.pause(0.001) # Small pause to process GUI event
    
    if first_time:
        input()
        first_time = False


    ser.write([TAKE_PICTURE_CODE])

    capture = last_img.get()
    while capture == None:
        capture = last_img.get()
    print("found")
    img.save(esp_image_folder_path / (row["img-id"]+".png"))

