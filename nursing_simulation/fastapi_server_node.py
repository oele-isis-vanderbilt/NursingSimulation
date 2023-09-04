from multiprocessing import Queue
from queue import Full
from threading import Thread
from typing import Dict, List, Optional

import cv2
import uvicorn
from chimerapy.engine import DataChunk, Node
from chimerapy.orchestrator import sink_node
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles


@sink_node(name="NursingSimulation_FastAPIVideoNode")
class FastAPIVideoNode(Node):
    def __init__(
        self,
        static_dir_path,
        frame_key="frame",
        port=8000,
        name="FastAPINode",
    ):
        super().__init__(name=name)
        self.static_dir_path = static_dir_path
        self.port = port
        self.frame_key = frame_key
        self.app: Optional[FastAPI] = None
        self.thread: Optional[Thread] = None
        self.videos = {}

    def setup(self):
        self.app = FastAPI()
        self.app.mount(
            "/static",
            StaticFiles(directory=self.static_dir_path),
            name="static",
        )
        self.app.add_api_route(
            "/video-feed/{name}", self.generate_video_feed, methods=["GET"]
        )
        self.app.add_api_route("/feed-info", self.get_feed_info, methods=["GET"])
        # Serve the application at the given port
        self.thread = Thread(
            target=self._start_app,
            kwargs={
                "port": self.port,
                "app": self.app,
            },
            daemon=True,
        )
        self.thread.start()

    @staticmethod
    def _start_app(app, port):
        print(f"Starting FastAPI server on port {port}")
        uvicorn.run(app, port=port)

    def step(self, data_chunks: Dict[str, DataChunk]) -> None:
        for name, data_chunk in data_chunks.items():
            img = data_chunk.get(self.frame_key)["value"]

            if name not in self.videos:
                self.videos[name] = Queue(maxsize=100)

            try:
                self.videos[name].put_nowait(cv2.imencode(".jpg", img)[1].tobytes())
            except Full:
                self.videos[name].get_nowait()
                self.videos[name].put_nowait(cv2.imencode(".jpg", img)[1].tobytes())

    async def generate_video_feed(self, name: str):
        async def video_feed_generator():
            while True:
                frames_queue = self.videos.get(name)
                frame = frames_queue.get()
                yield (
                    b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

        if name not in self.videos:
            return Response(status_code=404, content="Video not found")

        return StreamingResponse(
            video_feed_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    async def get_feed_info(self) -> Dict[str, List[str]]:
        return {
            "feeds": list(self.videos.keys()),
        }

    def teardown(self):
        self.app = None
        self.thread = None
        self.videos = {}
