# Basic interactive LLM to voice pipeline project

## Demo (turn on the sound)

https://github.com/zigzag1001/LLM-to-TTS/assets/72932714/8a05de3e-0428-424c-826e-2b234450662d



## Requirements
- llama-cpp-python (+ compatible models)
- TTS
- PyAudio

### Usage
1. `python3 main.py`
2. Select model using numbers
3. Enter prompt
4. Repeat 3

#### Notes
- Currently using/tested mistral dolphin
- For tts using Xtts_v2
- Often came across torch not detecting CUDA
- To fix torch, install using [this](https://pytorch.org/get-started/locally/)

