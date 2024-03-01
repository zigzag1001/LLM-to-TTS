from llama_cpp import Llama
from TTS.api import TTS
import wave
import sys
import pyaudio
import os
import time
import threading

tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=True)

if not os.path.exists('./voice'):
    os.makedirs('./voice')

if not os.path.exists('./models'):
    os.makedirs('./models')
    print("Please add models to the ./models folder")
    exit()

files = os.listdir('./models')
for i, file in enumerate(files):
    print(f"{i+1}: {file}")
choice = int(input("Choose a model: "))-1

llm = Llama(
        model_path=f'./models/{files[choice]}',
        chat_format="chatml",
        n_gpu_layers=-1,
        n_ctx=2048,
)

prompt = "Question: "
response = ""
messages = [
        {
            "role": "system",
            "content": "You are a popular ai vtuber and streamer. your name is Nano, short for NanoNova. you have a bratty and fun personality. you are talking to your chat. your responses should be short. do not use proper graammar or capitalization. you are a vtuber so you are always in character"
        },
]

def play_audio(n):
    with wave.open(f"./voice/{n}.wav", 'rb') as f:
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                        channels=f.getnchannels(),
                        rate=f.getframerate(),
                        output=True)
        data = f.readframes(1024)
        while data:
            stream.write(data)
            data = f.readframes(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
    os.remove(f"./voice/{n}.wav")

def gen_wav(responsearr, n):
    tts.tts_to_file(text=responsearr[n],
                    file_path=f"./voice/{n}.wav",
                    speaker_wav=["G:\\apps\\llms\\output000.wav"],
                    language="en",
                    split_sentences=False,
    )


def main():
    while True:

        prompt = input("Question: ")
        response = ""
        messages.append({"role": "user", "content": prompt})

        if prompt == "exit":
            break

        stream = llm.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=400,
        )

        for s in stream:
            parsed = s['choices'][0]['delta']
            keys = list(parsed.keys())
            if len(keys) > 0 and not "assistant" == parsed[keys[0]]:
                print(parsed[keys[0]], end="", flush=True)
                response += parsed[keys[0]]

        messages.append({"role": "assistant", "content": response})

        # split response into sentences
        split = []
        index = 0
        for c in range(len(response)):
            if response[c] in [".", "!", "?", "\n"]:
                split.append(response[index:c+1])
                index = c+1
        split.append(response[index:])

        responsearr = split.copy()

        i = 0
        while i < len(responsearr)-1:
            if len(responsearr[i]) > 250:
                temp = [responsearr[i][j:j+250] for j in range(0, len(responsearr[i]), 250)]
                del responsearr[i]
                for t in temp[::-1]:
                    responsearr.insert(i, t)
            elif len(responsearr[i] + responsearr[i+1]) <= 250:
                responsearr[i] += responsearr[i+1]
                responsearr.pop(i+1)
            else:
                i += 1



        gen_wav(responsearr, 0)

        audio_thread = threading.Thread(target=play_audio, args=(0,))
        audio_thread.start()

        for i in range(1, len(responsearr)):
            gen_wav(responsearr, i)
            audio_thread.join()
            audio_thread = threading.Thread(target=play_audio, args=(i,))
            audio_thread.start()


if __name__ == "__main__":
    main()
