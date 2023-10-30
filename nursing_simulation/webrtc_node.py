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
    ) -> None:
        super().__init__(name=name)
        self.webrtc_service = WebRTCService(host=host, port=port)
        self.app = None
        self.first_step = False
        self.frames_queue = None
        self.video_chunk_key = video_chunk_key
        self.audio_chunk_key = audio_chunk_key
        self.video_save_prefix = video_save_prefix
        self.audio_save_prefix = audio_save_prefix

    async def setup(self) -> None:
        self.app = self.webrtc_service.get_app()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.webrtc_service.host, self.webrtc_service.port)
        await site.start()
        self.first_step = False
        self.frames_queue = asyncio.Queue()

    async def step(self) -> DataChunk:
        if not self.first_step:
            await self.webrtc_service.add_client(self.frames_queue)
            self.first_step = True

        try:
            if self.state.fsm == "STOPPED":
                await self.webrtc_service.remove_client(self.frames_queue)

            wrtc_data = await asyncio.wait_for(self.frames_queue.get(), timeout=1)
            if wrtc_data.kind == "video":
                self.save_video(self.video_save_prefix, wrtc_data.data, fps=30)
                ret_chunk = DataChunk()
                ret_chunk.add(self.video_chunk_key, wrtc_data.data, "image")
                return ret_chunk
            elif wrtc_data.kind == "audio":
                self.save_audio_v2(
                    name=self.audio_save_prefix,
                    data=wrtc_data.data["sound"],
                    channels=wrtc_data.data["channels"],
                    framerate=wrtc_data.data["sample_rate"],
                    sampwidth=wrtc_data.data["samp_width"],
                    nframes=wrtc_data.data["num_frames"],
                )
                return None
        except asyncio.QueueEmpty:
            return None
        except asyncio.TimeoutError:
            return None

    async def teardown(self) -> None:
        await self.webrtc_service.teardown()
        self.app = None
        self.first_step = False
        self.frames_queue = None
