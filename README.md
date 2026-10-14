<img src="logo.jpg" alt="VoiceSim logo" width="100" />

# VoiceSim

Operate Microsoft Flight Simulator aircraft controls with push-to-talk voice commands, especially when flying in VR. VoiceSim records your microphone, transcribes speech through **OpenRouter**, and asks a separately configurable text model to select a command from its built-in aircraft catalog using structured JSON. The app validates the result and sends the SimConnect event to the simulator. No command configuration is needed.

Examples:

- "Set comm radio to one one niner point two five"
- "Set nav radio two to one one oh point seven five"
- "Increase flaps"
- "Toggle landing lights"
- "Toggle parking brakes"
- "Autopilot heading hold on"
- "Set heading to forty five degrees"
- "Set autopilot vertical speed to minus five hundred feet per minute"
- "Raise the landing gear"
- "Set squawk to seven seven zero zero"
- "Set altimeter pressure to one thousand thirteen point two five hectopascals"

## Requirements

- Windows and Microsoft Flight Simulator on the same PC. Tested platform: Windows 11 and MSFS 2020. MSFS 2024 and FSX have not been verified.
- A microphone and speakers/headset.
- Internet access and an [OpenRouter API key](https://openrouter.ai/keys) with access/credits for your selected models. Audio and transcripts are sent to OpenRouter and its selected model providers.

## Install

The Windows release runs without installing Python, pip, or any modules.

1. Download `VoiceSim.exe` or `VoiceSim-windows-x64.zip` from the project's [releases](https://github.com/paruljain/voice_sim/releases).
2. Put the executable in a writable folder such as `Documents\VoiceSim`. If using the ZIP, extract it first.
3. Double-click `VoiceSim.exe`. It creates `VoiceSim.ini` beside itself. The first launch shows a message asking you to configure your key.
4. Open `VoiceSim.ini` in a text editor, set `api_key` in `[openrouter]`, and save it. This file contains your models, triggers, and audio devices. Aircraft commands are built into the app.
5. Launch `VoiceSim.exe` again and start MSFS.

Keep your `VoiceSim.ini` when replacing the executable with a new release. Setup never overwrites it. The console stays open on startup errors when launched by double-clicking.

Alternatively, create the settings from PowerShell:

```powershell
.\VoiceSim.exe --setup
```

Edit `VoiceSim.ini` and set `api_key` under `[openrouter]`. Alternatively, set the key for the current PowerShell session:

```powershell
$env:OPENROUTER_API_KEY = 'your-openrouter-key'
```

The environment variable takes precedence over the config key. Settings are saved beside the executable; notification audio and native libraries are embedded. Launching from another folder works. Device-listing commands do not require an API key or a running simulator.

### Configuration format

`VoiceSim.ini` is plain text using `key = value` entries grouped into `[openrouter]`, `[trigger]`, and `[audio]`. Open it in Notepad or any text editor. Values need no quotes, commas between lines, or programming syntax. Lines beginning with `#` or `;` are comments. Leave optional device IDs or language blank to use defaults. Restart VoiceSim after editing.

The generated file includes comments explaining each preference. For example:

```ini
[openrouter]
api_key = your-openrouter-key
speech_to_text_model = openai/whisper-large-v3
generation_model = openai/gpt-4.1-mini

[trigger]
key = alt
joystick_id =
joystick_button =

[audio]
record_device_id =
playback_device_id =

```

Settings are read as data. Misspelled settings, duplicate entries, and invalid device IDs produce a descriptive startup error. The command catalog is supplied automatically.

## Choose your models

These exact IDs were checked against OpenRouter's live catalog on **October 13, 2026**:

| Stage | Config setting | Default | Other examples |
| --- | --- | --- | --- |
| Speech-to-text | `speech_to_text_model` | [`openai/whisper-large-v3`](https://openrouter.ai/openai/whisper-large-v3) | [`openai/gpt-4o-mini-transcribe`](https://openrouter.ai/openai/gpt-4o-mini-transcribe), [`mistralai/voxtral-mini-transcribe`](https://openrouter.ai/mistralai/voxtral-mini-transcribe) |
| Command generation | `generation_model` | [`openai/gpt-4.1-mini`](https://openrouter.ai/openai/gpt-4.1-mini) | [`google/gemini-2.5-flash`](https://openrouter.ai/google/gemini-2.5-flash) |

```ini
[openrouter]
speech_to_text_model = openai/whisper-large-v3
generation_model = openai/gpt-4.1-mini
speech_language =
request_timeout_seconds = 30
```

Edit these entries in the `[openrouter]` section. Use full `provider/model` IDs. Speech-to-text uses OpenRouter's dedicated [`/audio/transcriptions` endpoint](https://openrouter.ai/docs/guides/overview/multimodal/stt); choose a **transcription** model. A general model that accepts audio in chat is not necessarily compatible. Browse the current [transcription model catalog](https://openrouter.ai/models?output_modalities=transcription), or query `https://openrouter.ai/api/v1/models?output_modalities=transcription`. Generation uses `/chat/completions` and requires a model/provider supporting [structured outputs with JSON Schema](https://openrouter.ai/docs/guides/features/structured-outputs). Both generation examples above support this. VoiceSim requests routing only to providers supporting the required parameters.

`speech_language` is an optional language code such as `en`; leave it blank to detect the language. Transcription preserves the spoken language rather than forcing an English translation. Generation receives an English aircraft catalog; try your chosen models with your language before relying on them. `request_timeout_seconds` sets the read timeout for each API call, with a separate 10-second connection timeout. For generation, prefer models that answer briefly without lengthy reasoning; truncated or malformed outputs are ignored.

Availability, provider behavior, latency, and prices can change. Check each linked model page for current pricing. Each spoken command makes one transcription request and, if a transcript is returned, one generation request. The full supported catalog and a few examples count toward generation input usage. The app does not make an extra model call to select a category.

## Use

```powershell
.\VoiceSim.exe
```

Start MSFS before or after VoiceSim; it waits for a SimConnect connection. In the cockpit, hold **Alt**, wait for the double beep, speak one command, and release Alt. The console shows the transcript, generated event, and whether it was sent. Latency depends on your models and network. Press **Ctrl+C** to quit.

The model must select an allowed catalog ID and a numeric argument or null. The app maps the ID to an event and checks argument presence, type, range, and encoding before execution. Unsupported or unclear speech returns no command. Invalid, multiple, or truncated responses are ignored. A sent event does not guarantee the aircraft supports it; some aircraft use custom controls.

### Trigger and audio configuration

- **Keyboard:** change `key` in `[trigger]` to a [keyboard key name](https://github.com/boppreh/keyboard/blob/master/keyboard/_canonical_names.py). Use one key; combinations such as Ctrl+P are not supported. Avoid a key already bound in MSFS.
- **Joystick:** run `.\VoiceSim.exe --list-joysticks`, then `.\VoiceSim.exe --list-joystick-buttons ID`. Set `joystick_id` and `joystick_button` in `[trigger]` to the reported integers. A configured joystick takes precedence over the keyboard. Only events from that joystick are accepted. Leave both values blank to use the keyboard.
- **Microphone/output:** run `.\VoiceSim.exe --list-audio-devices`. Set `record_device_id` in `[audio]` to an input ID or `playback_device_id` to an output ID. Blank selects the Windows default device. Device IDs can change when USB devices or VR headsets reconnect; list them again if necessary.

A close microphone or headset reduces engine noise. Check Windows microphone permissions and recording levels. Run `.\VoiceSim.exe --help` for all options.

### Troubleshooting

- **Authentication/credits:** HTTP 401 means check the OpenRouter key; HTTP 402 means check credits/access.
- **Model errors:** check the full ID, that the STT model supports transcription, and that the generation model/provider supports JSON Schema structured outputs. Try one of the examples above. Check [OpenRouter status](https://status.openrouter.ai/) for outages.
- **Timeout/rate limit:** try again after the current request ends or increase the timeout. VoiceSim does not automatically replay commands.
- **Recording errors:** verify microphone access and the device ID. Recording errors are reported without waiting forever for a failed recording thread.
- **No cockpit change:** check the transcript and generated event in the console. Verify the aircraft supports that SimConnect event. Speak a single instruction at a time.
- **Radio tuning:** the shipped COM/NAV events accept MHz with at most two decimals, such as `119.25` or `109.70`. Three-decimal 8.33 kHz COM channels require events absent from this pinned package. VoiceSim handles BCD encoding locally. ADF complete-frequency setters take kHz with one decimal place; squawk codes use digits 0 through 7.
- **Package check:** run `.\VoiceSim.exe --self-test` to verify bundled libraries, the notification sound, HTTPS certificates, and aircraft catalog. This does not contact OpenRouter or connect to MSFS.
- **Settings not saved:** keep the executable in a writable folder; avoid running it directly inside a ZIP or placing it under Program Files.

## Built-in aircraft commands

The bundled catalog contains **730 aircraft events**, of which **718 are enabled for execution**. It is generated from the exact pinned [Python-SimConnect EventList](https://github.com/odwdinc/Python-SimConnect/blob/master/SimConnect/EventList.py), supplemented with parameter metadata from the [Microsoft Flight Simulator SDK](https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Event_IDs.htm). Invalid placeholder names are omitted. Camera, slew, failure, mission, ATC, multiplayer, and other non-aircraft categories are excluded.

Engine controls, flight controls, autopilot, fuel systems, avionics, instruments, lights, miscellaneous aircraft systems, and helicopter controls are included. The twelve unavailable entries are retained with reasons: missing SDK contracts or events the SDK marks unsupported. They are not offered to the model or allowed to execute.

```powershell
.\VoiceSim.exe --list-commands
```

The model receives the complete supported catalog with descriptions, argument types/units/ranges, and a few examples. Strict JSON Schema restricts the selection to a compact numeric catalog ID; VoiceSim resolves the event name locally and validates the argument. Radio/ADF frequency encoding, squawk BCD, altimeter pressure scaling, and Mach scaling happen in the app. Events with a secondary SDK selector use only the legacy/default selector supported by the wrapper; explicit additional indexes are not supported. Speak one instruction at a time.

The built-in catalog is embedded in the executable and requires no configuration or runtime download. Aircraft-specific custom events and multi-argument transports beyond the wrapper's single DWORD are not covered. The model's context limit applies; generation uses temperature 0 and allows 128 output tokens.

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

All executable options also work with `python voice_sim.py`. Settings live beside the source files when running from source. `VoiceSim.ini`, virtual environments, and release artifacts are ignored by Git.

Run the offline regression tests (no API key, audio hardware, or simulator required):

```powershell
python -m unittest discover -s tests -v
```

The tests mock API requests and audio devices; live OpenRouter and simulator integration require your credentials and hardware.

### Maintain the aircraft catalog

Developers can regenerate `aircraft_commands.json` with:

```powershell
python generate_catalog.py
```

The generator reads aircraft events from the installed SimConnect package, fetches the SDK event tables, and records their URLs and hashes. It combines documented argument metadata with explicit conversion rules. Review catalog changes, especially argument contracts, and run the regression tests before releasing. The tests check that the catalog matches the pinned package, that all enabled events resolve, and that JSON selection, argument validation, and conversions agree. Changing the SimConnect version requires regenerating and reviewing the catalog. Existing user preferences remain separate from the built-in catalog.

### Build a Windows release

Build on 64-bit Windows using 64-bit Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe build_release.py
```

The build runs regression tests, packages `dist\VoiceSim.exe`, and checks an isolated copy using `--help`, `--self-test`, and `--setup`. It verifies settings persist outside the temporary extraction folder and are preserved on repeated setup. It also creates `dist\VoiceSim-windows-x64.zip` and `dist\SHA256SUMS.txt`. The bundle includes SimConnect.dll, PyAudio, pygame, keyboard, requests, Python, the default preferences, aircraft catalog, and notification sound. User keys/settings are never included.

The **Build Windows release** GitHub Actions workflow performs the same build and uploads downloadable artifacts. Run it manually from the Actions tab, or push a `v*` tag. It does not automatically publish a GitHub Release; attach the ZIP and checksum file to a release when ready. Live speech and cockpit behavior still require testing with a microphone, API key, and MSFS.
