import asyncio

from aiohttp import web
from chimerapy.engine import DataChunk, Node
from chimerapy.orchestrator import source_node

from nursing_simulation.webrtc_service import WebRTCService


@source_node(name="NS_WRTC")
class WebRTCNode(Node):
    """WebRTC Node that serves a video/audio stream from a browser to the pipeline"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        video_chunk_key: str = "frame",
        audio_chunk_key: str = "audio",
        video_save_prefix: str = "screen-capture",
        audio_save_prefix: str = "audio-capture",
        name: str = "NS_WRTC",
    ):
        super().__init__(name=name)
        self.webrtc_service = WebRTCService(host=host, port=port)
        self.app = None
        self.first_step = False
        self.video_frames_queue = None
        self.video_chunk_key = video_chunk_key
        self.audio_chunk_key = audio_chunk_key
        self.video_save_prefix = video_save_prefix
        self.audio_save_prefix = audio_save_prefix

    async def setup(self):
        self.app = self.webrtc_service.get_app()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.webrtc_service.host, self.webrtc_service.port)
        await site.start()
        self.first_step = False
        self.video_frames_queue = asyncio.Queue()

    async def step(self) -> DataChunk:
        if not self.first_step:
            await self.webrtc_service.add_video_client(self.video_frames_queue)
            self.first_step = True

        try:
            frame = await asyncio.wait_for(self.video_frames_queue.get(), timeout=1)
            self.save_video(self.video_save_prefix, frame, fps=30)
            ret_chunk = DataChunk()
            ret_chunk.add(self.video_frames_queue, frame, "image")
            return ret_chunk
        except asyncio.QueueEmpty:
            return None
        except asyncio.TimeoutError:
            return None

    async def teardown(self):
        await self.webrtc_service.teardown()
        self.app = None
        self.first_step = False
        self.video_frames_queue = None
