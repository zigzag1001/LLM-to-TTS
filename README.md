# Basic interactive LLM to voice pipeline project

---
Currently changing lots of things so README is probably outdated in some parts
---
Create an issue and i might update it & help
---

### Demo (turn on the sound)



https://github.com/zigzag1001/LLM-to-TTS/assets/72932714/f1d20287-4ed4-4533-9879-c7b2e9d4f557




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

### Install
- clone repo
- create venv and pip install requirements.txt into it
- - [dev version of discord.py](https://github.com/Rapptz/discord.py#installing)
- find devices (TTS input, output) (Im currently using `VoiceMeeter Input`, `VoiceMeeter Out`)
- `python get_audio_devices.py`
- copy the names of the devices into appropriate place in main.py and bot.py
- main.py gets the input, bot.py gets the output
- create .env and set TOKEN="your discord bot token"
- download llama.cpp compatible models into ./models
- edit config.json

### Usage
- launch both main and bot
- press enter in main to start
- join vc and ping bot join
- `@yourbot join`
- it probably wont work because i forgot to mention something

#### Notes
- Currently using/tested mistral dolphin 2.1 and nous hermes 2
- For tts using ~~Xtts_v2~~ Vits (theres probably better options)
- Often came across torch not detecting CUDA
- To fix torch, install using [this](https://pytorch.org/get-started/locally/)
