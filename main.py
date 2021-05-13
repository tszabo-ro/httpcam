import time
from pathlib import Path
from datetime import datetime

import quart
from quart import Quart, render_template, websocket

import cv2
import base64

# define a video capture object

app = Quart(__name__)


class Camera:
    def __init__(self):
        self.scale = 100
        self.camera = cv2.VideoCapture(0)
        self.frame_counter = 0

        now = datetime.now()
        self.session_id = now.strftime("%d-%m-%Y_%H-%M-%S")

        Path("frames/{}".format(self.session_id)).mkdir(parents=True, exist_ok=True)

    def grab_frame(self) -> str:
        retval, image = self.camera.read()

        width = int(image.shape[1] * self.scale / 100)
        height = int(image.shape[0] * self.scale / 100)
        dim = (width, height)

        # resize image
        resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

        return resized

    def grab_frame_base64(self) -> str:
        frame = self.grab_frame()

        retval, buffer = cv2.imencode('.png', frame)
        return base64.b64encode(buffer).decode("utf-8")

    def save_frame(self):
        filename = 'frames/{}/frame_{}.jpg'.format(self.session_id, self.frame_counter)
        print("Saving to {}".format(filename))
        cv2.imwrite(filename, self.grab_frame())
        self.frame_counter += 1


camera = Camera()


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


@app.websocket("/frames")
async def ws():
    while True:
        frame = camera.grab_frame_base64()
        await websocket.send_json({"frame": "{}".format(frame)})
        time.sleep(0.05)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
