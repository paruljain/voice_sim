<img src="logo.jpg" alt="VoiceSim logo" width="100" />

# VoiceSim

Operate Microsoft Flight Simulator aircraft controls with push-to-talk voice commands, especially when flying in VR. VoiceSim records your microphone, transcribes speech through **OpenRouter**, uses a separately configurable text model to generate a SimConnect event, and sends that event to the simulator.

Examples:

- "Set comm radio to one one niner point two five"
- "Set nav radio two to one one oh point seven five"
- "Increase flaps"
- "Toggle landing lights"
- "Toggle parking brakes"
- "Autopilot heading hold on"
- "Set heading to forty five degrees"
- "Set autopilot vertical speed to minus five hundred feet per minute"

## Requirements

- Windows and Microsoft Flight Simulator on the same PC. The original project was tested with Windows 11 and MSFS 2020; MSFS 2024 and FSX have not been verified with this update.
- Python **3.10 or newer**. Python 3.11 or 3.12 is a practical choice for Windows audio package wheels; newer Python versions may need native build tools if wheels are unavailable.
- A microphone and speakers/headset.
- Internet access and an [OpenRouter API key](https://openrouter.ai/keys) with access/credits for your selected models. Audio and transcripts are sent to OpenRouter and its selected model providers.

## Install

Download or clone this repository, open PowerShell in its folder, and run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config_sample.py config.py
```

Edit `config.py` and set `openrouter_api_key`. Alternatively, set the key for the current PowerShell session:

```powershell
$env:OPENROUTER_API_KEY = 'your-openrouter-key'
```

The environment variable takes precedence over the config key. `config.py` is ignored by Git. If it is missing, VoiceSim copies the sample on startup without removing the sample. Settings and the notification sound resolve relative to the app, so launching from another folder works.

### Upgrading the original GPT-3 version

Reinstall requirements in your virtual environment. Keep your existing trigger and audio device settings in `config.py`, replace `open_ai_api_key` with `openrouter_api_key`, and add the model settings below. Missing model settings use the new defaults. An OpenAI API key does not authenticate with OpenRouter. The retired GPT-3 completion endpoint and hard-coded Whisper translation call are no longer used.

## Choose your models

These exact IDs were checked against OpenRouter's live catalog on **October 13, 2026**:

| Stage | Config setting | Default | Other examples |
| --- | --- | --- | --- |
| Speech-to-text | `speech_to_text_model` | [`openai/whisper-large-v3`](https://openrouter.ai/openai/whisper-large-v3) | [`openai/gpt-4o-mini-transcribe`](https://openrouter.ai/openai/gpt-4o-mini-transcribe), [`mistralai/voxtral-mini-transcribe`](https://openrouter.ai/mistralai/voxtral-mini-transcribe) |
| Command generation | `generation_model` | [`openai/gpt-4.1-mini`](https://openrouter.ai/openai/gpt-4.1-mini) | [`google/gemini-2.5-flash`](https://openrouter.ai/google/gemini-2.5-flash) |

```python
'speech_to_text_model': 'openai/whisper-large-v3',
'generation_model': 'openai/gpt-4.1-mini',
'speech_language': None,
'request_timeout_seconds': 30,
```

Add those entries inside the `config` dictionary. Use full `provider/model` IDs. Speech-to-text uses OpenRouter's dedicated [`/audio/transcriptions` endpoint](https://openrouter.ai/docs/guides/overview/multimodal/stt); choose a **transcription** model. A general model that accepts audio in chat is not necessarily compatible. Browse the current [transcription model catalog](https://openrouter.ai/models?output_modalities=transcription), or query `https://openrouter.ai/api/v1/models?output_modalities=transcription`. Generation uses `/chat/completions` and needs a text chat model.

`speech_language` is an optional language code such as `'en'`; `None` lets the transcription model detect it. Transcription preserves the spoken language rather than forcing an English translation. Generation is instructed with an English command table; try your chosen models with your language before relying on them. `request_timeout_seconds` sets the read timeout for each API call, with a separate 10-second connection timeout. For generation, prefer models that answer briefly without lengthy reasoning; truncated or malformed outputs are ignored.

Availability, provider behavior, latency, and prices can change. Check each linked model page for current pricing. Each spoken command makes one transcription request and, if a transcript is returned, one generation request. The command table counts toward generation input usage.

## Use

```powershell
.\.venv\Scripts\python.exe voice_sim.py
```

Start MSFS before or after VoiceSim; it waits for a SimConnect connection. In the cockpit, hold **Alt**, wait for the double beep, speak one command, and release Alt. The console shows the transcript, generated event, and whether it was sent. Latency depends on your models and network. Press **Ctrl+C** to quit.

Generated commands must match an event in `prompt.py` with the expected parameter count. Unsupported speech returns no command. Invalid, multiple, or truncated commands are ignored. A sent event does not guarantee the aircraft supports it; some aircraft use custom controls.

### Trigger and audio configuration

- **Keyboard:** change `trigger_key` to a lowercase [keyboard key name](https://github.com/boppreh/keyboard/blob/master/keyboard/_canonical_names.py). Use one key; combinations such as Ctrl+P are not supported. Avoid a key already bound in MSFS.
- **Joystick:** run `python list_joysticks.py`, then `python list_joystick_buttons.py ID`. Set `joystick_id` and `button` to the reported integers. A configured joystick takes precedence over the keyboard. Only events from that joystick are accepted. Set both values to `None` to use the keyboard.
- **Microphone/output:** run `python list_audio_devices.py`. Set `audio_record_device_id` to an input ID or `audio_playback_device_id` to an output ID. `None` selects the Windows default device. Device IDs can change when USB devices or VR headsets reconnect; list them again if necessary.

Use your virtual environment's Python for these helper scripts too. A close microphone or headset reduces engine noise. Check Windows microphone permissions and recording levels.

### Troubleshooting

- **Authentication/credits:** HTTP 401 means check the OpenRouter key; HTTP 402 means check credits/access. The old `open_ai_api_key` setting is not used.
- **Model errors:** check the full ID and that the STT model supports the transcription endpoint. Try one of the examples above. Check [OpenRouter status](https://status.openrouter.ai/) for outages.
- **Timeout/rate limit:** try again after the current request ends or increase the timeout. VoiceSim does not automatically replay commands.
- **Recording errors:** verify microphone access and the device ID. Recording errors are reported without waiting forever for a failed recording thread.
- **No cockpit change:** check the transcript and generated event in the console. Verify the aircraft supports that SimConnect event. Speak a single instruction at a time.
- **Radio tuning:** the supplied legacy `COM_RADIO_SET` / `NAV*_RADIO_SET` events accept MHz with at most two decimals, such as `119.25` or `109.70`. Three-decimal 8.33 kHz COM channels require different SimConnect events and are not supported by the supplied table.
- **PyAudio installation:** upgrade pip and use a Python version with Windows wheels; otherwise PyAudio needs PortAudio and native build tools.

## Add voice commands

Edit the lookup table in `prompt.py`. Add a line in the form `spoken example: EVENT_NAME` or `spoken example: EVENT_NAME,123`. Parameterized examples tell the model to substitute the number you request. The app derives its allowed events and parameter requirements from this table; adding a new event does not require a second allowlist edit.

Find supported events in [Python-SimConnect's EventList](https://github.com/odwdinc/Python-SimConnect/blob/master/SimConnect/EventList.py). Test additions in the simulator with your chosen models. The old 2,049-token GPT-3 limit is gone; the selected model's context limit applies. Generation asks for one plain event, uses temperature 0, and allows 128 output tokens.

## Development

The requirements pin the latest stable PyPI releases checked on October 13, 2026. `keyboard` and `SimConnect` retain their versions because no newer stable releases were listed. `open_ai.py` retains a compatibility alias for the old `getCommand` import; the implementation lives in `open_router.py`.

Run the offline regression tests (no API key, audio hardware, or simulator required):

```powershell
python -m unittest discover -s tests -v
```

The tests mock API requests and audio devices; live OpenRouter and simulator integration require your credentials and hardware.

## Contributing

Contributions are welcome; please open a pull request. Questions and suggestions: paruljain@hotmail.com.
