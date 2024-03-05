# Basic interactive LLM to voice pipeline project

## Demo (turn on the sound)

https://github.com/zigzag1001/LLM-to-TTS/assets/72932714/8a05de3e-0428-424c-826e-2b234450662d



## Requirements
- llama-cpp-python (+ compatible models)
- TTS
- PyAudio
- OpenAi whisper
- ===For the bot part:
- [discord-ext-voice-recv](https://github.com/imayhaveborkedit/discord-ext-voice-recv)
- [dev version of discord.py](https://github.com/Rapptz/discord.py#installing)
- [virtual audio cable + voicemeeter](https://vb-audio.com/)
- python_dotenv

### Usage
1. `python3 main.py`
2. Select model using numbers
3. Enter prompt
4. Repeat 3

#### Notes
- Currently using/tested mistral dolphin 2.1 and nous hermes 2
- For tts using ~~Xtts_v2~~ Vits (theres probably better options)
- Often came across torch not detecting CUDA
- To fix torch, install using [this](https://pytorch.org/get-started/locally/)

##### discord bot
- You can technically put a discord bot in the pipeline
- bot.py file is how i did it (very jank)
- you just have to create a .env with your TOKEN="yourtoken"
- and edit the code that gets device indexes (`cable` is where the prompt goes, `microphone` is where the TTS responds)
- so discord->Cable Input->Cable Output->whisper->LLM->TTS->VoiceMeeter Input->VoiceMeeter Output->discord
