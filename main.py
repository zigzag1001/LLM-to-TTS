from llama_cpp import Llama
from TTS.api import TTS
from time import sleep
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
system_prompt = {
        "role": "system",
        "content": llm_conf["system_prompt"]
}
messages = [system_prompt]


def play_audio(n, device=None):
    with wave.open(f"./voice/{n}.wav", 'rb') as f:
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(device)
        print(info.get('name'), info.get('index'))
        stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                        channels=f.getnchannels(),
                        rate=int(f.getframerate()*1),
                        output=True,
                        output_device_index=device
                        )
        data = f.readframes(1024)
        while data:
            stream.write(data)
            data = f.readframes(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
        print(f"Device {device} worked")
    if device is None:
        os.remove(f"./voice/{n}.wav")


def gen_wav(responsearr, n):
    try:
        tts.tts_to_file(text=responsearr[n] + "\n\n",
                        file_path=f"./voice/{n}.wav",
                        speaker_wav=tts_conf["speaker_wav"],
                        language="en",
                        split_sentences=False,
                        )
    except Exception as e:
        print(e)
        tts.tts_to_file(text="filtered",
                        file_path=f"./voice/{n}.wav",
                        speaker_wav=tts_conf["speaker_wav"],
                        language="en",
                        split_sentences=False,
                        )


def main():
    while True:

        prompt = input("Question: ")
        response = ""

        if prompt in ["exit", "quit", "stop", "q", ":q"]:
            break

        messages.append({"role": "user", "content": prompt})

        if len(messages) > 5:
            messages.pop(1)

        stream = llm.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=llm_conf["max_tokens"],
            temperature=llm_conf["temperature"],
        )

        for s in stream:
            parsed = s['choices'][0]['delta']
            keys = list(parsed.keys())
            if len(keys) > 0 and not "assistant" == parsed[keys[0]]:
                print(parsed[keys[0]], end="", flush=True)
                response += parsed[keys[0]]

        messages.append({"role": "assistant", "content": response})

        if len(messages) > 5:
            messages.pop(1)

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

        p = pyaudio.PyAudio()
        devices = p.get_device_count()
        cable = None
        for i in range(devices):
            device_info = p.get_device_info_by_index(i)
            if "CABLE Input (VB-Audio Virtual C" in device_info.get('name'):
                print(f"Device {device_info.get('index')} is {device_info.get('name')}")
                cable = device_info.get('index')
                break

        gen_wav(responsearr, 0)

        audio_thread = threading.Thread(target=play_audio, args=(0, cable, ))
        audio_thread.start()

        for i in range(1, len(responsearr)):
            gen_wav(responsearr, i)
            audio_thread.join()
            audio_thread = threading.Thread(target=play_audio, args=(i, cable, ))
            audio_thread.start()

        # devices = [4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 25, 27, 29, 32, 34]
        # gen_wav(responsearr, 0)
        #
        # for i in devices:
        #     play_audio(0, i)




if __name__ == "__main__":
    main()
