import asyncio

from discord import PCMVolumeTransformer, FFmpegPCMAudio
from youtube_dl import YoutubeDL

_ytdl_format_options = dict(
    format='bestaudio/best',
    outtmpl='%(extractor)s-%(id)s-%(title)s.%(ext)s',
    restrictfilenames=True,
    noplaylist=True,
    nocheckcertificate=False,
    ignoreerrors=False,
    logtostderr=False,
    quiet=True,
    no_warnings=True,
    cachedir=False,
    source_address='0.0.0.0'
)

_ffmpeg_options = dict(
    options='-vn',
    before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
)

ytdl = YoutubeDL(_ytdl_format_options)

class TYDLSource(PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.title = data.get('title')
        self.url = data.get('url')
        self.uploader = data.get('uploader')
        self.duration_seconds = data.get('duration')

    @property
    def duration(self):
        if not self.duration_seconds:
            return '0:0'
        second = self.duration_seconds % 60
        minute = self.duration_seconds // 60
        hour = self.duration_seconds // (60 * 60)
        if hour > 0:
            return '{}:{:02}:{:02}'.format(hour, minute, second)
        else:
            return '{:02}:{:02}'.format(minute, second)

    @classmethod
    async def create(cls, query, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info('ytsearch:' + query, download=not stream)
        )

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(FFmpegPCMAudio(filename, **_ffmpeg_options), data=data)
