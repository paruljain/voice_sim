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

- Windows and Microsoft Flight Simulator on the same PC. Tested platform: Windows 11 and MSFS 2020. MSFS 2024 and FSX have not been verified.
- A microphone and speakers/headset.
- Internet access and an [OpenRouter API key](https://openrouter.ai/keys) with access/credits for your selected models. Audio and transcripts are sent to OpenRouter and its selected model providers.

## Install

The Windows release runs without installing Python, pip, or any modules.

1. Download `VoiceSim.exe` or `VoiceSim-windows-x64.zip` from the project's [releases](https://github.com/paruljain/voice_sim/releases).
2. Put the executable in a writable folder such as `Documents\VoiceSim`. If using the ZIP, extract it first.
3. Double-click `VoiceSim.exe`. It creates `config.py` and `commands.txt` beside itself. The first launch shows a message asking you to configure your key.
4. Open `config.py` in a text editor, set `openrouter_api_key`, and save it. You can also change the models, trigger, and audio device IDs here.
5. Launch `VoiceSim.exe` again and start MSFS.

Keep your `config.py` and `commands.txt` when replacing the executable with a new release. Setup never overwrites these files. The console stays open on startup errors when launched by double-clicking.

Alternatively, create the settings from PowerShell:

```powershell
.\VoiceSim.exe --setup
```

Edit `config.py` and set `openrouter_api_key`. Alternatively, set the key for the current PowerShell session:

```powershell
$env:OPENROUTER_API_KEY = 'your-openrouter-key'
```

The environment variable takes precedence over the config key. Settings are saved beside the executable; notification audio and native libraries are embedded. Launching from another folder works. Device-listing commands do not require an API key or a running simulator.

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
.\VoiceSim.exe
```

Start MSFS before or after VoiceSim; it waits for a SimConnect connection. In the cockpit, hold **Alt**, wait for the double beep, speak one command, and release Alt. The console shows the transcript, generated event, and whether it was sent. Latency depends on your models and network. Press **Ctrl+C** to quit.

Generated commands must match an event in `commands.txt` with the expected parameter count. Unsupported speech returns no command. Invalid, multiple, or truncated commands are ignored. A sent event does not guarantee the aircraft supports it; some aircraft use custom controls.

### Trigger and audio configuration

- **Keyboard:** change `trigger_key` to a lowercase [keyboard key name](https://github.com/boppreh/keyboard/blob/master/keyboard/_canonical_names.py). Use one key; combinations such as Ctrl+P are not supported. Avoid a key already bound in MSFS.
- **Joystick:** run `.\VoiceSim.exe --list-joysticks`, then `.\VoiceSim.exe --list-joystick-buttons ID`. Set `joystick_id` and `button` to the reported integers. A configured joystick takes precedence over the keyboard. Only events from that joystick are accepted. Set both values to `None` to use the keyboard.
- **Microphone/output:** run `.\VoiceSim.exe --list-audio-devices`. Set `audio_record_device_id` to an input ID or `audio_playback_device_id` to an output ID. `None` selects the Windows default device. Device IDs can change when USB devices or VR headsets reconnect; list them again if necessary.

A close microphone or headset reduces engine noise. Check Windows microphone permissions and recording levels. Run `.\VoiceSim.exe --help` for all options.

### Troubleshooting

- **Authentication/credits:** HTTP 401 means check the OpenRouter key; HTTP 402 means check credits/access.
- **Model errors:** check the full ID and that the STT model supports the transcription endpoint. Try one of the examples above. Check [OpenRouter status](https://status.openrouter.ai/) for outages.
- **Timeout/rate limit:** try again after the current request ends or increase the timeout. VoiceSim does not automatically replay commands.
- **Recording errors:** verify microphone access and the device ID. Recording errors are reported without waiting forever for a failed recording thread.
- **No cockpit change:** check the transcript and generated event in the console. Verify the aircraft supports that SimConnect event. Speak a single instruction at a time.
- **Radio tuning:** the supplied legacy `COM_RADIO_SET` / `NAV*_RADIO_SET` events accept MHz with at most two decimals, such as `119.25` or `109.70`. Three-decimal 8.33 kHz COM channels require different SimConnect events and are not supported by the supplied table.
- **Package check:** run `.\VoiceSim.exe --self-test` to verify bundled libraries, the notification sound, and HTTPS certificates. This does not contact OpenRouter or connect to MSFS.
- **Settings not saved:** keep the executable in a writable folder; avoid running it directly inside a ZIP or placing it under Program Files.

## Add voice commands

Edit the lookup table in `commands.txt` beside the executable. Add a line in the form `spoken example: EVENT_NAME` or `spoken example: EVENT_NAME,123`. Parameterized examples tell the model to substitute the number you request. The app derives its allowed events and parameter requirements from this table; adding a new event does not require a second allowlist edit. `prompt.py` contains the default table used to create this file.

Find supported events in [Python-SimConnect's EventList](https://github.com/odwdinc/Python-SimConnect/blob/master/SimConnect/EventList.py). Test additions in the simulator with your chosen models. The selected model's context limit applies. Generation asks for one plain event, uses temperature 0, and allows 128 output tokens.

## Development

The requirements pin the latest stable PyPI releases checked on October 13, 2026. The API implementation lives in `open_router.py`.

### Run from source

Developers need Python **3.10 or newer**. Python 3.11 or 3.12 is a practical choice for Windows audio wheels. Download or clone this repository and run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe voice_sim.py --setup
.\.venv\Scripts\python.exe voice_sim.py
```

All executable options also work with `python voice_sim.py`. Settings live beside the source files when running from source. `config.py`, `commands.txt`, virtual environments, and release artifacts are ignored by Git.

Run the offline regression tests (no API key, audio hardware, or simulator required):

```powershell
python -m unittest discover -s tests -v
```

The tests mock API requests and audio devices; live OpenRouter and simulator integration require your credentials and hardware.

### Build a Windows release

Build on 64-bit Windows using 64-bit Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe build_release.py
```

The build runs regression tests, packages `dist\VoiceSim.exe`, and checks an isolated copy using `--help`, `--self-test`, and `--setup`. It verifies settings persist outside the temporary extraction folder and are preserved on repeated setup. It also creates `dist\VoiceSim-windows-x64.zip` and `dist\SHA256SUMS.txt`. The bundle includes SimConnect.dll, PyAudio, pygame, keyboard, requests, Python, the default config, and the notification sound. User keys/settings are never included.

The **Build Windows release** GitHub Actions workflow performs the same build and uploads downloadable artifacts. Run it manually from the Actions tab, or push a `v*` tag. It does not automatically publish a GitHub Release; attach the ZIP and checksum file to a release when ready. Live speech and cockpit behavior still require testing with a microphone, API key, and MSFS.

## Contributing

Contributions are welcome; please open a pull request. Questions and suggestions: paruljain@hotmail.com.
