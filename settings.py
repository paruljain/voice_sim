"""Load settings relative to the application, never the working directory."""
import math
import os
from pathlib import Path
import runpy
import shutil
import sys

RESOURCE_DIR = Path(__file__).resolve().parent
# One-file builds extract resources into a temporary folder. Keep user settings
# beside the actual executable so they survive exit and subsequent launches.
def application_directory():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else RESOURCE_DIR


APP_DIR = application_directory()
DEFAULTS = {
    'trigger_key': 'alt',
    'trigger_joystick_button': {'joystick_id': None, 'button': None},
    'openrouter_api_key': '',
    'speech_to_text_model': 'openai/whisper-large-v3',
    'generation_model': 'openai/gpt-4.1-mini',
    'speech_language': None,
    'request_timeout_seconds': 30,
    'audio_playback_device_id': None,
    'audio_record_device_id': None,
}


def load_config():
    path = APP_DIR / 'config.py'
    if not path.exists():
        shutil.copyfile(RESOURCE_DIR / 'config_sample.py', path)
        print(f'Created {path}. Set your OpenRouter key before starting VoiceSim.')
    commands_path = APP_DIR / 'commands.txt'
    if not commands_path.exists():
        import prompt
        commands_path.write_text(prompt.prompt, encoding='utf-8')
        print(f'Created {commands_path}. Edit this file to add voice commands.')
    # Read the source each time; same-size edits can otherwise reuse stale bytecode.
    user_config = runpy.run_path(str(path)).get('config')
    if not isinstance(user_config, dict):
        raise ValueError('config.py must define a config dictionary.')
    return {**DEFAULTS, **user_config}


def validate_api_config(config):
    key = os.environ.get('OPENROUTER_API_KEY') or config.get('openrouter_api_key')
    if not isinstance(key, str) or not key.strip() or key.startswith('Insert '):
        raise ValueError('Set OPENROUTER_API_KEY or openrouter_api_key in config.py.')
    for field in ('speech_to_text_model', 'generation_model'):
        model = config.get(field)
        if not isinstance(model, str) or '/' not in model or not model.strip():
            raise ValueError(f'{field} must be a full OpenRouter model ID (provider/model).')
    timeout = config.get('request_timeout_seconds', 30)
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('request_timeout_seconds must be a positive number.')
    return key.strip()
