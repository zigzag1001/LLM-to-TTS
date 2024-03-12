import time
time1 = time.time()

from llama_cpp import Llama
from TTS.api import TTS
import threading
import pyaudio
import whisper
import audioop
import random
import wave
import json
import sys
import os

print(f"Imports took {time.time()-time1} seconds")

with open("config.json", "r") as f:
    config = json.load(f)
    llm_conf = config["LLM"]
    tts_conf = config["TTS"]

device = "cuda" if tts_conf["gpu"] else "cpu"

time1 = time.time()
tts = TTS(model_name=tts_conf["model_name"]).to(device)
print(f"TTS load took {time.time()-time1} seconds")

time1 = time.time()
w_model = whisper.load_model("small.en")
print(f"Whisper load took {time.time()-time1} seconds")

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

time1 = time.time()
llm = Llama(
    model_path=llm_file,
    chat_format=llm_conf["chat_format"],
    n_gpu_layers=llm_conf["n_gpu_layers"],
    n_ctx=llm_conf["n_ctx"],
    verbose=False,
)

print(f"LLM load took {time.time()-time1} seconds")

prompt = "Question: "
response = ""
system_prompt = {
        "role": "system",
        "content": llm_conf["system_prompt"]
}

def record_audio(device=None):
    global audio_thread
    with wave.open(f"./voice/recorded.wav", 'wb') as f:
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(device)
        stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    input_device_index=device
                    )
        # get silence threshold
        # ???
        silence_threshold = 10
        silences_detected = 0
        silences_allowed = 25
        frames = []

        # wait for user to start speaking (> silence threshold)
        print("Speak now...")
        while True:
            data = stream.read(2048)
            if audioop.rms(data, 2) > silence_threshold:
                frames.append(data)
                if audio_thread is not None:
                    audio_thread.join()
                break

        # wait for user to stop speaking (< silence threshold)
        print("Recording...")
        while True:
            data = stream.read(1024)
            frames.append(data)
            if audioop.rms(data, 2) < silence_threshold:
                silences_detected += 1
                print(f"Silence detected: {silences_detected}")
                if silences_detected > silences_allowed:
                    break
            else:
                silences_detected = 0

        print("Recording stopped")

        # data = stream.read(44100*5)
        stream.stop_stream()
        stream.close()
        p.terminate()
        f.setnchannels(1)
        f.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        f.setframerate(44100)
        f.writeframes(b''.join(frames))


def play_audio(n, device=None):
    with wave.open(f"./voice/{n}.wav", 'rb') as f:
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(device)
        stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                        channels=f.getnchannels(),
                        rate=int(f.getframerate()*1.1),
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
    os.remove(f"./voice/{n}.wav")


def gen_wav(responsearr, n):
    time1 = time.time()
    try:
        tts.tts_to_file(text=responsearr[n] + "\n\n",
                        file_path=f"./voice/{n}.wav",
                        speaker_wav=tts_conf["speaker_wav"],
                        language=tts_conf["language"],
                        split_sentences=False,
                        )
    except Exception as e:
        print(e)
        tts.tts_to_file(text="filtered",
                        file_path=f"./voice/{n}.wav",
                        speaker_wav=tts_conf["speaker_wav"],
                        language=tts_conf["language"],
                        split_sentences=False,
                        )
    print(f"TTS took {time.time()-time1} seconds")


global audio_thread
audio_thread = None

def main():
    global audio_thread
    input("Press enter to start")
    messages = [system_prompt]
    while True:

        p = pyaudio.PyAudio()
        devices = p.get_device_count()
        cable = None
        microphone = None
        for i in range(devices):
            device_info = p.get_device_info_by_index(i)
            # Set this string to your microphone
            if "CABLE Output (VB-Audio Virtual" in device_info.get('name') and microphone is None:
                microphone = device_info.get('index')
            # Set this string to the input of the output device
            # (the bot will play audio from this device)
            # if "VoiceMeeter Input" in device_info.get('name') and cable is None:
            #     cable = device_info.get('index')
            if "CABLE Input (VB-Audio Virtual" in device_info.get('name') and cable is None:
                cable = device_info.get('index')
            if cable is not None and microphone is not None:
                break

        """)))"""
        # prompt = input("Question: ") # Type input
        # prompt_no_user = prompt
        prompt = "Question: "
        if prompt.lower() in ["exit", "quit", "stop", "q", ":q"]:
            break

        # record_audio(microphone) # Record from device input

        # bot.py records audio from each user
        prompt = ""
        prompt_no_user = ""
        prompts = {}
        while os.listdir("./voice/user") == []:
            time.sleep(0.1)
        time1 = time.time()
        for file in os.listdir("./voice/user"):
            # prompts.append(w_model.transcribe(f"./voice/user/{file}")["text"])
            prompts[file[:-4]] = w_model.transcribe(f"./voice/user/{file}")["text"]
            if audio_thread is not None:
                audio_thread.join()
            os.remove(f"./voice/user/{file}")
        print(f"Transcription took {time.time()-time1} seconds")

        for key, value in prompts.items():
            print(f"User {key}: {value}")
            prompt += f"{key}: {value}\n"
            prompt_no_user += value
        # end bot.py recording implementation

        print(f"Prompt ===> {prompt}")

        hallucinations = ["thanks for watching", "thank you.", "bye."]

        if prompt == "" or any(h in prompt_no_user.strip().lower() for h in hallucinations):
            print("No prompt detected")
            continue

        commands = ["reset"]
        clean_prompt = "".join(char for char in prompt_no_user if char.isalpha()).lower().strip()
        print(clean_prompt)
        if clean_prompt in commands:
            if clean_prompt == "reset":
                messages = [system_prompt]
            continue

        response = ""

        messages.append({"role": "user", "content": prompt})

        # limit messages to 10
        if len(messages) > 10:
            messages.pop(1)

        # make chatting more interesting
        if len(messages) > 5 and random.randint(0, 4) == 4:
            messages = [system_prompt]
            print("Resetting messages")

        time1 = time.time()
        stream = llm.create_chat_completion(
            messages=messages,
            stream=True,
            max_tokens=llm_conf["max_tokens"],
            temperature=llm_conf["temperature"],
        )

        print("Response ===>")

        for s in stream:
            parsed = s['choices'][0]['delta']
            keys = list(parsed.keys())
            if len(keys) > 0 and not "assistant" == parsed[keys[0]]:
                print(parsed[keys[0]], end="", flush=True)
                response += parsed[keys[0]]
        print("\n===========\n")

        if ":" in response:
            response = response.split(":")[1]
            print("rm :")
        if "#" in response:
            response = response.split("#")[0]
            print("rm #")

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

        print(f"LLM took {time.time()-time1} seconds")

        if audio_thread is not None:
            audio_thread.join()

        gen_wav(responsearr, 0)


        audio_thread = threading.Thread(target=play_audio, args=(0, cable, ), daemon=True)
        audio_thread.start()

        for i in range(1, len(responsearr)):
            gen_wav(responsearr, i)
            audio_thread.join()
            audio_thread = threading.Thread(target=play_audio, args=(i, cable, ))
            audio_thread.start()




if __name__ == "__main__":
    main()
