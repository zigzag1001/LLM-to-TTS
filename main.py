if __name__ == "__main__":
    import time
    time1 = time.time()

    USE_WHISPER = True
    USE_TTS = True

    from llama_cpp import Llama
    if USE_TTS:
        from RealtimeTTS import TextToAudioStream, CoquiEngine
    from get_audio_devices import print_audio_devices
    if USE_WHISPER:
        from faster_whisper import WhisperModel
    import random
    import json
    import os


    print(f"Imports took {time.time()-time1} seconds")

    ttstime = 0

    # Load config
    with open("config.json", "r") as f:
        config = json.load(f)
        llm_conf = config["LLM"]
        tts_conf = config["TTS"]
        audio_conf = config["audio"]

    device = "cuda" if tts_conf["gpu"] else "cpu"

    if USE_TTS:
        # Load tts model
        time1 = time.time()

        tts = CoquiEngine(
            speed=1.3,
        )
        tts_stream = TextToAudioStream(
            engine=tts,
            output_device_index=audio_conf["device"],
        )
        print(f"TTS load took {time.time()-time1} seconds")

    if USE_WHISPER:
        # Load whisper model
        time1 = time.time()
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

    def write_response():
        global messages
        print("Writing response")
        result = ""
        pure_response = llm.create_chat_completion(
                messages=messages,
                max_tokens=200,
                stop=["\n\n"],
                temperature=1,
                stream=True,
                # top_p=0.99,
                # top_k=100,
                # min_p=0,
                # typical_p=0.2,
                # presence_penalty=1,
                # frequency_penalty=2,
                # repeat_penalty=1.5
        )
        for chunk in pure_response:
            if (text_chunk := chunk["choices"][0]["delta"].get("content")) is not None:
                result += text_chunk
                print(text_chunk, end="", flush=True)
                yield text_chunk

        if (random.random() < 0.5):
            result = result.lower()

        result = "".join([c for c in result if c.isalnum() or c in [",", ".", "!", "?", " "]])

        if result == "":
            yield "..."
        else:
            print(result)
            messages.append({"role": "assistant", "content": result})

        print("Response done")


    def main():
        global messages
        global ttstime
        global system_prompt
        print("Started")

        # Clean user audio folder
        clean_folder("./voice/user")

        messages = [
                {"role": "system", "content": "You are a VTuber.\
                        You are streaming on Twitch.\
                        You have a fun and kinda random personality.\
                        you are talking to your audience.\
                        dont repeat patterns such as talking in all caps,\
                        your responses should be very short and non repetitive.\
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
                # wait for user audio
                while os.listdir("./voice/user") == []:
                    time.sleep(0.1)


                # transcribe into prompts dict
                time1 = time.time()
                prompts = {}

                for file in os.listdir("./voice/user"):

                    transcipt = ""
                    segments, _ = w_model.transcribe(f"./voice/user/{file}")
                    for segment in segments:
                        transcipt += segment.text + " "
                    prompts[file[:-4]] = transcipt

                    os.remove(f"./voice/user/{file}")

                print(f"Transcription took {time.time()-time1} seconds")

                # ignore whisper hallucinations
                hallucinations = ["thanks for watching", "thank you.", "bye.", "thank you very much."]

                # remove prompts with hallucinations
                temp_prompts = prompts.copy()
                for prompt in temp_prompts.keys():
                    if prompts[prompt] == "" or any(h in prompts[prompt].strip().lower() for h in hallucinations):
                        del prompts[prompt]


                prompt = "\n".join([f"{prompt}: {prompts[prompt]}" for prompt in prompts.keys()])
            else:
                prompt = input("Prompt: ")
                ttstime = time.time()

            messages.append({"role": "user", "content": prompt})


            print(prompt)


            # llm implementation

            text_stream = write_response()

            tts_stream.feed(text_stream)

            tts_stream.play_async(
                fast_sentence_fragment=True
            )
            while tts_stream.is_playing():
                time.sleep(0.5)
            print("Done playing")
            tts_stream.stop()

            if len(messages) > 10:
                messages = messages[-10:]



    main()
