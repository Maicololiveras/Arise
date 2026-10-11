"""Pinned model assets shared by online setup and offline packaging."""
QWEN_REV = 'a615a81362316d7b9f5a7a9c4313adfdf9b54588'
WHISPER_SHA = '9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794'
SOURCES = {
    'piper.zip': ('https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip', 'f3c58906402b24f3a96d92145f58acba6d86c9b5db896d207f78dc80811efcea'),
    'models/es_MX-ald-medium.onnx': ('https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/es/es_MX/ald/medium/es_MX-ald-medium.onnx', '019b3803293c93e34a206dd2e53a3889209a514e786fd7144f7b70196c579b63'),
    'models/es_MX-ald-medium.onnx.json': ('https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json', 'efab736e62e5321dd5d063d1b46e63c59ce655419816355b81d025c1a8d6b03c'),
    'licenses/PIPER-VOICE-MODEL-CARD.txt': ('https://huggingface.co/rhasspy/piper-voices/resolve/375a0fe641dea077c2a47b4e9a056d6da521eed3/es/es_MX/ald/medium/MODEL_CARD', '1f0694ceb3f1e78c1e2ee0e2d5da40f19f965bc638e1b4fb4fca9bdca420d713'),
    'models/small.pt': (f'https://openaipublic.azureedge.net/main/whisper/models/{WHISPER_SHA}/small.pt', WHISPER_SHA),
    'models/dialogue.gguf': (f'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/{QWEN_REV}/qwen2.5-1.5b-instruct-q4_k_m.gguf', '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'),
    'llama.zip': ('https://github.com/ggml-org/llama.cpp/releases/download/b10991/llama-b10991-bin-win-cpu-x64.zip', '8f1b7bcc1df032bb0c5759e3db5c67969f20c6f061aa0efec70de7bfa00fbf37'),
}

