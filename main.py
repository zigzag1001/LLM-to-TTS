import time
time1 = time.time()

from llama_cpp import Llama
from TTS.api import TTS
from get_audio_devices import print_audio_devices
import threading
import pyaudio
# import whisper
from faster_whisper import WhisperModel
import random
import wave
import json
import os

USE_WHISPER = True

print(f"Imports took {time.time()-time1} seconds")

# Load config
with open("config.json", "r") as f:
    config = json.load(f)
    llm_conf = config["LLM"]
    tts_conf = config["TTS"]
    audio_conf = config["audio"]

device = "cuda" if tts_conf["gpu"] else "cpu"

# Load tts model
time1 = time.time()
tts = TTS(model_name=tts_conf["model_name"]).to(device)
print(f"TTS load took {time.time()-time1} seconds")

# Load whisper model
time1 = time.time()
# w_model = whisper.load_model("small.en")
w_model = WhisperModel("small.en", device="cuda", compute_type="float16")
print(f"Whisper load took {time.time()-time1} seconds")

# Ensure directories exist
if not os.path.exists('./voice'):
    os.makedirs('./voice')

# Load or choose LLM model
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

# Load LLM model
time1 = time.time()
llm = Llama(
    model_path=llm_file,
    # chat_format=llm_conf["chat_format"],
    n_gpu_layers=llm_conf["n_gpu_layers"],
    n_ctx=llm_conf["n_ctx"],
    verbose=False,
)

print(f"LLM load took {time.time()-time1} seconds")

# get audio devices
if audio_conf["device"] is None:
    print("\n\nPlease select an audio device to play audio into:\n\n")
    print_audio_devices()
    input_device = int(input("\n\nDevice: "))
    audio_conf["device"] = input_device
    # update config
    with open("config.json", "r") as f:
        config = json.load(f)
        config["audio"]["device"] = input_device
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

# cleans path if exists
# if not exists, creates path
def clean_folder(path):
    if os.path.exists(path):
        for file in os.listdir(path):
            os.remove(f"{path}/{file}")
    else:
        os.makedirs(path)

# Plays audio from a file in the voice folder
# through the specified device
# delete the file after playing
def play_audio(n, device=None):
    with wave.open(f"./voice/{n}.wav", 'rb') as f:
        p = pyaudio.PyAudio()
        info = p.get_device_info_by_index(device)
        stream = p.open(format=p.get_format_from_width(f.getsampwidth()),
                        channels=f.getnchannels(),
                        # rate=int(f.getframerate()*1.1),
                        rate=int(f.getframerate()),
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
    # for file in os.listdir("./voice/user/"):
    #     if file.endswith(".wav"):
    #         os.remove(f"./voice/user/{file}")


# Generates audio from a response and saves it to a file in the voice folder
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
    global system_prompt
    print("Started")

    # Clean user audio folder
    clean_folder("./voice/user")

    messages = [
            {"role": "system", "content": "You are a VTuber.\
                    You are streaming on Twitch.\
                    You have a fun and kinda random personality.\
                    you are talking to your audience.\
                    your responses should be very short and non repetitive.\
                    dont repeat patterns such as talking in all caps,\
                    and any other speech pattern that might get annoying.\
                    your name is NanoNova, or Nano for short.\
                    your responses are voiced by a text-to-speech model.\
                    your audience talks to you through speech to text.\
                    dont ask your audience questions.\
                    if you dont know what to say, just say something random.\
                    if a prompt starts with [username]: it means the user is talking to you.\
                    multiple prompts can be given at once.\
                    "},
            ]

    while True:

        if USE_WHISPER:
            if audio_thread is not None:
                audio_thread.join()

            # wait for user audio
            while os.listdir("./voice/user") == []:
                time.sleep(0.1)

            total_time = time.time()

            # transcribe into prompts dict
            time1 = time.time()
            prompts = {}

            for file in os.listdir("./voice/user"):

                # prompts[file[:-4]] = w_model.transcribe(f"./voice/user/{file}")["text"]
                transcipt = ""
                segments, _ = w_model.transcribe(f"./voice/user/{file}")
                for segment in segments:
                    transcipt += segment.text + " "
                prompts[file[:-4]] = transcipt

                os.remove(f"./voice/user/{file}")

            print(f"Transcription took {time.time()-time1} seconds")

            # ignore whisper hallucinations
            hallucinations = ["thanks for watching", "thank you.", "bye.", "Thank you very much."]

            # remove prompts with hallucinations
            temp_prompts = prompts.copy()
            for prompt in temp_prompts.keys():
                if prompts[prompt] == "" or any(h in prompts[prompt].strip().lower() for h in hallucinations):
                    del prompts[prompt]


            prompt = "\n".join([f"{prompt}: {prompts[prompt]}" for prompt in prompts.keys()])
        else:
            prompt = input("Prompt: ")
            total_time = time.time()

        messages.append({"role": "user", "content": prompt})


        print(prompt)


        # llm implementation

        time1 = time.time()

        response = llm.create_chat_completion(
                messages=messages,
                max_tokens=250,
                stop=["\n\n"],
                temperature=1,
                # top_p=0.99,
                # top_k=100,
                # min_p=0,
                # typical_p=0.2,
                # presence_penalty=1,
                # frequency_penalty=2,
                # repeat_penalty=1.5
        )

        print(f"LLM took {time.time()-time1} seconds")

        response = response["choices"][0]["message"]["content"]

        if "*" in response:
            response = response.split("*")[0] + response.split("*")[-1]

        if (random.random() < 0.5):
            response = response.lower()

        response = "".join([c for c in response if c.isalnum() or c in [",", ".", "!", "?", " "]])

        print(response)

        messages.append({"role": "assistant", "content": response})

        gen_wav([response], 0)


        if audio_thread is not None:
            audio_thread.join()

        audio_thread = threading.Thread(target=play_audio, args=(0, audio_conf["device"]))
        audio_thread.start()

        print(f"Total time: {time.time()-total_time}")



if __name__ == "__main__":
    main()
