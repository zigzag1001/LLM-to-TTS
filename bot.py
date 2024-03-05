import discord
from discord.ext import commands, voice_recv, tasks
from discord.utils import get
from discord.opus import Decoder

import threading
import pyaudio
import asyncio
# import audioop
import queue
import wave
import time
import os
from dotenv import load_dotenv

data_queue = queue.Queue()

load_dotenv()

TOKEN = os.getenv('TOKEN')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

ffmpeg_opts = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
}


p = pyaudio.PyAudio()
devices = p.get_device_count()
cable = None
microphone = None
for i in range(devices):
    device_info = p.get_device_info_by_index(i)
    if "CABLE Input (VB-Audio Virtual" in device_info.get('name') and cable is None:
        cable = device_info.get('index')
        print(f"Found cable at {cable}")
    if "VoiceMeeter Out" in device_info.get('name') and microphone is None:
        microphone = device_info.get('index')
        print(f"Found microphone at {microphone}")
    if cable is not None and microphone is not None:
        break
p.terminate()
""")"""
def is_connected(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    return voice_client and voice_client.is_connected()

p = pyaudio.PyAudio()
def process_pcm(device=None):
    CHANNELS = Decoder.CHANNELS
    SAMPLE_WIDTH = Decoder.SAMPLE_SIZE // CHANNELS
    SAMPLE_RATE = Decoder.SAMPLING_RATE
    stream = p.open(format=p.get_format_from_width(SAMPLE_WIDTH),
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    output=True,
                    output_device_index=device,
                    frames_per_buffer=1024
                    )
    while True:
        print(".", end="", flush=True)
        data = data_queue.get()
        stream.write(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

class PyAudioPCM(discord.AudioSource):
    def __init__(self, channels=2, rate=48000, chunk=960, input_device=1) -> None:
        p = pyaudio.PyAudio()
        self.chunks = chunk
        self.input_stream = p.open(format=pyaudio.paInt16,
                               channels=channels,
                               rate=rate,
                               input=True,
                               input_device_index=input_device,
                               frames_per_buffer=self.chunks
                               )

    def read(self) -> bytes:
        return self.input_stream.read(self.chunks)


async def play_audio_in_voice(ctx, device):
    vc = get(bot.voice_clients, guild=ctx.guild)
    vc.play(PyAudioPCM(input_device=device), after=lambda e: print(f'Player error: {e}') if e else None)


def listen_to_voice_channel(ctx, vc):
    if not vc.is_listening():
        vc.listen(voice_recv.BasicSink(callback), after=lambda e: print(f"Voice client stopped listening: {e}"))
    else:
        vc.stop_listening()
        vc.listen(voice_recv.BasicSink(callback), after=lambda e: print(f"Voice client stopped listening: {e}"))
        print("Already listening")

def callback(user, data):
    data_queue.put(data.pcm)


@bot.command(name='join', help='Listens to the voice channel', aliases=['j'])
async def join(ctx):
    if not is_connected(ctx):
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        listen_to_voice_channel(ctx, vc)
        listner_t = threading.Thread(target=process_pcm, args=(cable,), daemon=True)
        listner_t.start()
        await play_audio_in_voice(ctx, microphone)
    else:
        vc = get(bot.voice_clients, guild=ctx.guild)
        listen_to_voice_channel(ctx, vc)

@bot.command(name='stop', help='Leaves the voice channel', aliases=['st', 'leave', 'l'])
async def stop(ctx):
    await ctx.voice_client.disconnect()


bot.run(TOKEN)
