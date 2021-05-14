import time
from pathlib import Path
from datetime import datetime

import quart
from quart import Quart, render_template, websocket

import cv2
import base64

# define a video capture object

app = Quart(__name__)


class PIN:
    def __init__(self, number: int, enabled: bool):
        self.num = number
        self.enabled = enabled
        if self.enabled:
            from gpiozero import LED
            self.pin = LED(self.pin)

    def on(self):
        if self.enabled:
            self.pin.on()

    def off(self):
        if self.enabled:
            self.pin.off()


class Camera:
    def __init__(self, enable_gpio: bool):
        self.scale = 100
        self.camera = cv2.VideoCapture(0)
        self.frame_counter = 0
        self.light_pin = 2
        self.light_camera_delay_s = 0.5
        self.camera_pin = 3

        self.LED = PIN(self.light_pin, enable_gpio)
        self.GPIO_CAMERA = PIN(self.camera_pin, enable_gpio)

        now = datetime.now()
        self.session_id = now.strftime("%d-%m-%Y_%H-%M-%S")

        Path("frames/{}".format(self.session_id)).mkdir(parents=True, exist_ok=True)

    def grab_frame(self, enable_lights: bool) -> str:
        if enable_lights:
            self.LED.on()
            time.sleep(self.light_camera_delay_s)
            time.sleep(0.5)
            self.GPIO_CAMERA.on()

        retval, image = self.camera.read()

        if enable_lights:
            time.sleep(0.3)
            self.GPIO_CAMERA.off()
            self.LED.off()

        width = int(image.shape[1] * self.scale / 100)
        height = int(image.shape[0] * self.scale / 100)
        dim = (width, height)

        # resize image
        resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

        return resized

    def grab_frame_base64(self, enable_lights: bool = True) -> str:
        frame = self.grab_frame(enable_lights=enable_lights)

        retval, buffer = cv2.imencode('.png', frame)
        return base64.b64encode(buffer).decode("utf-8")

    def save_frame(self):
        filename = 'frames/{}/frame_{}.jpg'.format(self.session_id, self.frame_counter)
        cv2.imwrite(filename, self.grab_frame(enable_lights=True))
        self.frame_counter += 1

    def save_frame_with_name(self, dirname, filename):
        pathname = 'frames/{}/{}.jpg'.format(dirname, filename)

        Path("frames/{}".format(dirname)).mkdir(parents=True, exist_ok=True)

        cv2.imwrite(pathname, self.grab_frame(enable_lights=True))


camera = Camera(True)


@app.route("/")
async def hello():
    return await render_template("index.html", server_address=quart.request.host)


@app.route("/resize/<int:scale>")
async def json(scale):
    camera.scale = scale
    return {}


@app.route("/grab")
async def grab():
    camera.save_frame()
    return {}


@app.route("/grab_layer", methods=["GET"])
async def grab_layer():
    parameters = await quart.request.values

    if "layer" in parameters:
        layer = parameters.get('layer')
    else:
        layer = "frame_{}".format(camera.frame_counter)
        camera.frame_counter += 1

    if "uid" in parameters:
        uid = parameters.get('uid')
    else:
        uid = camera.session_id

    camera.save_frame_with_name(uid, layer)
    return {}


@app.websocket("/frames")
async def ws():
    while True:
        frame = camera.grab_frame_base64(enable_lights=False)
        await websocket.send_json({"frame": "{}".format(frame)})
        time.sleep(0.05)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
