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
else:
    for file in os.listdir(f"./voice/user"):
        os.remove(f"./voice/user/{file}")

user_threads = {}
ignored_users = []
p = pyaudio.PyAudio()
devices = p.get_device_count()
microphone = None


if os.path.exists("ignored_users.txt"):
    with open("ignored_users.txt", "r") as f:
        users = f.read().splitlines()
    for user in users:
        if user.isdigit():
            ignored_users.append(int(user))
        else:
            print(f"User {user} is not a valid ID")

for i in range(devices):
    device_info = p.get_device_info_by_index(i)
    # if "VoiceMeeter Out" in device_info.get('name'): # EDIT THIS STRING TO YOUR AUDIO PIPE METHOD
    if "CABLE Out" in device_info.get('name'):
        microphone = device_info.get('index')
        print(f"Found bots microphone at {microphone}")
        print(device_info.get('name'))
        break
p.terminate()

if microphone is None:
    print("No microphone found, exiting...")
    exit()


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
        self.user = user.name
        self.userid = user.id
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        global user_threads
        silence_threshold = 10
        silences_allowed = 13
        loud_allowed = 10
        q = user_threads[self.userid]["queue"]

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
            time.sleep(5)

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
    global ignored_users
    if user.id in ignored_users:
        return
    # if user thread does not exist, create it
    if user.id not in user_threads.keys():
        if user.guild.voice_client is None:
            return
        print(f"Creating thread for {user}")
        user_threads[user.id] = {}
        user_threads[user.id]["thread"] = record_user_audio(user)
        user_threads[user.id]["queue"] = queue.Queue()
        user_threads[user.id]["queue"].put(data.pcm)
        user_threads[user.id]["thread"].start()
    else:
        user_threads[user.id]["queue"].put(data.pcm)


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
        await play_audio_in_voice(ctx, microphone)
    else:
        vc = get(bot.voice_clients, guild=ctx.guild)
        listen_to_voice_channel(ctx, vc)

@bot.command(name='stop', help='Leaves the voice channel', aliases=['st', 'leave', 'l'])
async def stop(ctx=None, guild=None):
    global user_threads
    users = list(user_threads.keys())
    for user in users:
        print(f"Stopping thread for {user}")
        user_threads[user]["thread"].stop()
        del user_threads[user]
        if os.path.exists(f"./voice/user/{user}.wav"):
            print(f"Deleting {user}.wav")
            os.remove(f"./voice/user/{user}.wav")
    if guild is None:
        guild = ctx.guild
    voice_client = get(bot.voice_clients, guild=guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()

@bot.command(name='ignore', help='Ignores the specified user', aliases=['i'])
async def ignore(ctx, userid: str = None):
    global user_threads
    global ignored_users
    if userid is None:
        userid = ctx.author.id
    if not userid.isdigit():
        await ctx.send("Invalid user id")
        return
    userid = int(userid)
    if userid not in ignored_users:
        ignored_users.append(userid)
        await ctx.send(f"Ignoring {userid}")
        with open("ignored_users.txt", "a") as f:
            f.write(f"{userid}\n")
    if userid in user_threads.keys():
        user_threads[userid]["thread"].stop()
        del user_threads[userid]
        if os.path.exists(f"./voice/user/{userid}.wav"):
            os.remove(f"./voice/user/{userid}.wav")
    print(f"Ignoring {ctx.guild.get_member(int(userid)).name}")

@bot.command(name='unignore', help='Unignores the specified user', aliases=['ui'])
async def unignore(ctx, userid: str = None):
    global ignored_users
    if userid is None:
        userid = ctx.author.id
    if not userid.isdigit():
        await ctx.send("Invalid user id")
        return
    userid = int(userid)
    if userid in ignored_users:
        ignored_users.remove(userid)
        await ctx.send(f"Unignoring {userid}")
        with open("ignored_users.txt", "r") as f:
            lines = f.readlines()
        with open("ignored_users.txt", "w") as f:
            for line in lines:
                if line.strip("\n") != str(userid):
                    f.write(line)
    print(f"Unignoring {ctx.guild.get_member(int(userid)).name}")

@bot.command(name='ignoredlist', help='Lists the ignored users', aliases=['il', 'ignored'])
async def ignoredlist(ctx):
    global ignored_users
    users = []
    for user in ignored_users:
        users.append(ctx.guild.get_member(int(user)).name)
    await ctx.send(f"Ignored users: {users}")

@bot.command(name='activethreads', help='Lists the active threads', aliases=['at'])
async def activethreads(ctx):
    global user_threads
    active_threads = list(user_threads.keys())
    users = []
    for user in active_threads:
        users.append(ctx.guild.get_member(int(user)).name)
    await ctx.send(f"Active threads: {users}")

    
bot.run(TOKEN)
