import asyncio
import json
from pathlib import Path

import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay, MediaStreamTrack

STATIC_ROOT = Path(__file__).parent.parent / "static"


class VideoFramesArrayTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, track, on_frame):
        super().__init__()  # don't forget this!
        self.track = track
        self.array = np.random.randint(0, 255, size=(720, 1280, 3), dtype=np.uint8)
        self.on_frame = on_frame

    async def recv(self):
        frame = await self.track.recv()
        self.array = frame.to_ndarray(format="bgr24")
        if self.on_frame:
            self.on_frame(self.array)
        return frame


class AudioFramesArrayTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, track, on_frame):
        super().__init__()  # don't forget this!
        self.track = track
        self.on_frame = on_frame

    async def recv(self):
        frame = await self.track.recv()
        sound = frame.to_ndarray().tobytes()
        if self.on_frame:
            self.on_frame(
                {
                    "data": sound,
                    "sample_rate": frame.sample_rate,
                    "samp_width": frame.format.bytes,
                    "channels": frame.layout.channels,
                }
            )
        return frame


class WebRTCService:
    def __init__(
        self,
        host: str,
        port: int,
        mode: str = "dev",
    ):
        self.host = host
        self.port = port
        self.mode = mode
        self.video_client_queues = set()
        self.audio_client_queues = set()
        self.video_streaming_track = None
        self.pcs = set()

    def get_app(self):
        routes = []

        if self.mode == "dev":
            routes.extend(
                [
                    web.get("/", self.index),
                    web.get("/client.js", self.javascript),
                ]
            )

        routes.append(
            web.post("/offer", self._offer),
        )

        routes.append(
            web.post("/close", self._close),
        )

        app = web.Application()
        app.add_routes(routes)
        return app

    async def index(self, request: web.Request) -> web.Response:
        content = open(STATIC_ROOT / "index.html").read()
        return web.Response(content_type="text/html", text=content)

    async def javascript(self, request: web.Request) -> web.Response:
        content = open(STATIC_ROOT / "client.js", "r").read()
        return web.Response(content_type="application/javascript", text=content)

    async def _offer(self, request: web.Request) -> web.Response:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        self.pcs.add(pc)
        relay = MediaRelay()

        @pc.on("connectionstatechange")
        async def on_iceconnectionstatechange():
            if pc.connectionState == "failed":
                await pc.close()
                print("Connection failed, closing peer connection")

        @pc.on("track")
        def on_track(track):
            if track.kind == "video":
                array_track = VideoFramesArrayTrack(track, self.on_video_frame)
                pc.addTrack(relay.subscribe(array_track))
            elif track.kind == "audio":
                audio_track = AudioFramesArrayTrack(track, self.on_audio_frame)
                pc.addTrack(relay.subscribe(audio_track))

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        return web.Response(
            content_type="application/json",
            text=json.dumps(
                {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type,
                }
            ),
        )

    async def _close(self) -> web.Response:
        pass

    async def teardown(self):
        for pc in self.pcs:
            await pc.close()
        self.pcs.clear()

    async def add_video_client(self, queue):
        self.video_client_queues.add(queue)

    async def remove_video_client(self, queue):
        self.video_client_queues.discard(queue)

    async def add_audio_client(self, queue):
        self.audio_client_queues.add(queue)

    async def remove_audio_client(self, queue):
        self.audio_client_queues.discard(queue)

    async def on_audio_frame(self, frame):
        pass

    def on_video_frame(self, frame):
        for queue in self.video_client_queues:
            asyncio.create_task(queue.put(frame))
