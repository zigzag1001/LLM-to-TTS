from llama_cpp import Llama
from TTS.api import TTS
import threading
import pyaudio
import wave
import time
import json
import sys
import os

with open("config.json", "r") as f:
    config = json.load(f)
    llm_conf = config["LLM"]
    tts_conf = config["TTS"]

device = "cuda" if tts_conf["gpu"] else "cpu"

tts = TTS(model_name=tts_conf["model_name"]).to(device)

if not os.path.exists('./voice'):
    os.makedirs('./voice')

if llm_conf["model_path"] in ["", None]:
    if not os.path.exists('./models'):
        os.makedirs('./models')
        print("Please add models to the ./models folder or specify a model path in the config.json file.")
        exit()
elif os.path.isdir(llm_conf["model_path"]):
    files = os.listdir(llm_conf["model_path"])
    for i, file in enumerate(files):
        print(f"{i+1}: {file}")
    choice = int(input("Choose a model: "))-1
    llm_file = os.path.join(llm_conf["model_path"], files[choice])
else:
    llm_file = llm_conf["model_path"]

llm = Llama(
    model_path=llm_file,
    chat_format=llm_conf["chat_format"],
    n_gpu_layers=llm_conf["n_gpu_layers"],
    n_ctx=llm_conf["n_ctx"],
)

prompt = "Question: "
response = ""
messages = [
    {
        "role": "system",
        "content": llm_conf["system_prompt"]
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
                    speaker_wav=tts_conf["speaker_wav"],
                    language="en",
                    split_sentences=False,
                    )


def main():
    while True:

        prompt = input("Question: ")
        response = ""
        messages.append({"role": "user", "content": prompt})

        if prompt in ["exit", "quit", "stop", "q", ":q"]:
            break

        stream = llm.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=llm_conf["max_tokens"],
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
        lim = tts_conf["char_limit"]
        while i < len(responsearr)-1:
            if len(responsearr[i]) > lim:
                temp = [responsearr[i][j:j+lim]
                        for j in range(0, len(responsearr[i]), lim)]
                del responsearr[i]
                for t in temp[::-1]:
                    responsearr.insert(i, t)
            elif len(responsearr[i] + responsearr[i+1]) <= lim:
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
