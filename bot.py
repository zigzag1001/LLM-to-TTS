import discord
from discord.ext import commands, voice_recv, tasks
from discord.utils import get
from discord.opus import Decoder

import threading
import pyaudio
import asyncio
import audioop
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

if not os.path.exists(f"./voice/user"):
    os.makedirs(f"./voice/user")

user_threads = {}
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
# OLD stream into a device, then on the other end pick up audio as if the device was a microphone
# def process_pcm(device=None):
#     CHANNELS = Decoder.CHANNELS
#     SAMPLE_WIDTH = Decoder.SAMPLE_SIZE // CHANNELS
#     SAMPLE_RATE = Decoder.SAMPLING_RATE
#     stream = p.open(format=p.get_format_from_width(SAMPLE_WIDTH),
#                     channels=CHANNELS,
#                     rate=SAMPLE_RATE,
#                     output=True,
#                     output_device_index=device,
#                     frames_per_buffer=1024
#                     )
#     while True:
#         print(".", end="", flush=True)
#         data = data_queue.get()[1]
#         stream.write(data)
#     stream.stop_stream()
#     stream.close()
#     p.terminate()

# multi user wav saving
class record_user_audio(threading.Thread):

    CHANNELS = Decoder.CHANNELS
    SAMPLE_WIDTH = Decoder.SAMPLE_SIZE // CHANNELS
    SAMPLE_RATE = Decoder.SAMPLING_RATE

    def __init__(self, user):
        super(record_user_audio, self).__init__()
        self.user = user
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        global user_threads
        silence_threshold = 10
        silences_allowed = 16
        loud_allowed = 10
        q = user_threads[self.user]["queue"]

        while True:
            if self.stopped():
                return
            while os.path.exists(f"./voice/user/{self.user}.wav"):
                q.get()
            frames = []
            silences_detected = 0
            loud_detected = 0
            print("listening")
            while True:
                if self.stopped():
                    return
                self.data = q.get()
                if audioop.rms(self.data, 2) > silence_threshold:
                    frames.append(self.data)
                    loud_detected += 1
                    if loud_detected > loud_allowed:
                        break
                else:
                    loud_detected = 0
                    frames = []

            print("recording")
            while True:
                if self.stopped():
                    return
                self.data = q.get()
                frames.append(self.data)
                if audioop.rms(self.data, 2) < silence_threshold:
                    silences_detected += 1
                    print(silences_detected)
                    if silences_detected > silences_allowed:
                        break
                else:
                    silences_detected = 0

            print("Recording stopped")

            with wave.open(f"./voice/user/{self.user}.wav", 'wb') as f:
                f.setnchannels(self.CHANNELS)
                f.setsampwidth(self.SAMPLE_WIDTH)
                f.setframerate(self.SAMPLE_RATE)
                f.writeframes(b''.join(frames))



#         
# def record_audio(device=None):
#     CHANNELS = Decoder.CHANNELS
#     SAMPLE_WIDTH = Decoder.SAMPLE_SIZE // CHANNELS
#     SAMPLE_RATE = Decoder.SAMPLING_RATE
#     # get silence threshold
#     # ???
#     silence_threshold = 10
#     silences_detected = 0
#     silences_allowed = 25
#     frames = []
#
#     while True:
#         # wait for user to start speaking (> silence threshold)
#         print("Speak now...")
#         user = None
#         while True:
#             data = data_queue.get()[1]
#             if audioop.rms(data, 2) > silence_threshold:
#                 user = data_queue.get()[0]
#                 frames.append(data)
#                 break
#
#         # wait for user to stop speaking (< silence threshold)
#         print("Recording...")
#         while True:
#             if user is None:
#                 break
#             data = data_queue.get()[1]
#             if data_queue.get()[0] == user:
#                 frames.append(data)
#                 if audioop.rms(data, 2) < silence_threshold:
#                     silences_detected += 1
#                     print(f"Silence detected: {silences_detected}")
#                     if silences_detected > silences_allowed:
#                         break
#                 else:
#                     silences_detected = 0
#
#         print("Recording stopped")
#         if is None:
#             continue
#
#         # data = stream.read(44100*5)
#         with wave.open(f"./voice/{user}.wav", 'wb') as f:
#             f.setnchannels(CHANNELS)
#             f.setsampwidth(p.get_sample_size(SAMPLE_WIDTH))
#             f.setframerate(SAMPLE_RATE)
#             f.writeframes(b''.join(frames))

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
    global user_threads
    # if user thread does not exist, create it
    if str(user) not in user_threads.keys():
        print(f"Creating thread for {user}")
        user_threads[str(user)] = {}
        user_threads[str(user)]["thread"] = record_user_audio(str(user))
        user_threads[str(user)]["queue"] = queue.Queue()
        user_threads[str(user)]["queue"].put(data.pcm)
        user_threads[str(user)]["thread"].start()
    else:
        user_threads[str(user)]["queue"].put(data.pcm)


@bot.event
async def on_voice_state_update(member, before, after):
    bot_voice_channel = member.guild.voice_client
    if bot_voice_channel is None:
        return
    # stop if bot is alone in voice channel
    elif bot_voice_channel.channel.members == [bot.user]:
        print(f"{member.guild.name} - Bot alone, leaving...")
        await stop(None, member.guild)
        return
    # stop if bot is force disconnected from voice channel
    elif member == bot.user and member not in bot_voice_channel.channel.members:
        print(
            f"{member.guild.name} - Bot force disconnected, leaving..."
        )
        await stop(None, member.guild)
        return
    # if user leaves bots voice channel, stop thread and delete wav
    # TODO



@bot.command(name='join', help='Listens to the voice channel', aliases=['j'])
async def join(ctx):
    if not is_connected(ctx):
        vc = await ctx.author.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
        listen_to_voice_channel(ctx, vc)
        # listner_t = threading.Thread(target=process_pcm, args=(cable,), daemon=True)
        # listner_t.start()
        await play_audio_in_voice(ctx, microphone)
    else:
        vc = get(bot.voice_clients, guild=ctx.guild)
        listen_to_voice_channel(ctx, vc)

@bot.command(name='stop', help='Leaves the voice channel', aliases=['st', 'leave', 'l'])
async def stop(ctx=None, guild=None):
    global user_threads
    for user in user_threads.keys():
        print(f"Stopping thread for {user}")
        user_threads[user]["thread"].stop()
        if os.path.exists(f"./voice/user/{user}.wav"):
            print(f"Deleting {user}.wav")
            os.remove(f"./voice/user/{user}.wav")
    if guild is None:
        guild = ctx.guild
    voice_client = get(bot.voice_clients, guild=guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()


bot.run(TOKEN)
