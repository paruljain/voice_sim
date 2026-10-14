"""Read settings and voice commands from a single, non-executable INI file."""
import configparser
import math
import os
from pathlib import Path
import shutil
import sys

RESOURCE_DIR = Path(__file__).resolve().parent


def application_directory():
    # Packaged resources are temporary; user settings belong beside the EXE.
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else RESOURCE_DIR


APP_DIR = application_directory()
CONFIG_NAME = 'VoiceSim.ini'
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
SECTIONS = {
    'openrouter': {'api_key', 'speech_to_text_model', 'generation_model', 'speech_language', 'request_timeout_seconds'},
    'trigger': {'key', 'joystick_id', 'joystick_button'},
    'audio': {'record_device_id', 'playback_device_id'},
    'commands': None,
}


def _read_ini(path):
    parser = configparser.ConfigParser(interpolation=None, delimiters=('=',))
    parser.optionxform = str
    try:
        with path.open(encoding='utf-8-sig') as source:
            parser.read_file(source)
    except configparser.Error as exc:
        # Do not print parser exception text, which may contain an API key.
        line = getattr(exc, 'lineno', None)
        if line is None and getattr(exc, 'errors', None):
            line = exc.errors[0][0]
        location = f' at line {line}' if line else ''
        raise ValueError(f'{path.name} has invalid INI syntax{location}. Use [sections] and key = value; avoid duplicate entries.') from None
    except UnicodeError:
        raise ValueError(f'Save {path.name} as UTF-8 text.') from None
    if parser.defaults():
        raise ValueError(f'{path.name}: [DEFAULT] is not supported. Put values in their named sections.')
    for section in parser.sections():
        if section not in SECTIONS:
            raise ValueError(f'{path.name}: unknown section [{section}].')
        allowed = SECTIONS[section]
        if allowed is not None:
            for option in parser[section]:
                if option not in allowed:
                    raise ValueError(f'{path.name}: unknown setting [{section}] {option}.')
    return parser


def default_commands():
    return dict(_read_ini(RESOURCE_DIR / 'VoiceSim.sample.ini')['commands'])


def _device_id(parser, section, option):
    value = parser.get(section, option, fallback='').strip()
    if not value:
        return None
    try:
        result = int(value)
        if result < 0:
            raise ValueError
        return result
    except ValueError:
        raise ValueError(f'{CONFIG_NAME}: [{section}] {option} must be blank or a non-negative integer.') from None


def load_config():
    path = APP_DIR / CONFIG_NAME
    if not path.exists():
        shutil.copyfile(RESOURCE_DIR / 'VoiceSim.sample.ini', path)
        print(f'Created {path}. Set api_key in [openrouter] before starting VoiceSim.')
    parser = _read_ini(path)
    config = DEFAULTS.copy()
    for option, target in (
        ('api_key', 'openrouter_api_key'), ('speech_to_text_model', 'speech_to_text_model'),
        ('generation_model', 'generation_model'), ('speech_language', 'speech_language'),
    ):
        fallback = DEFAULTS[target] or ''
        config[target] = parser.get('openrouter', option, fallback=fallback).strip()
    config['speech_language'] = config['speech_language'] or None
    try:
        timeout = float(parser.get('openrouter', 'request_timeout_seconds', fallback='30'))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError
        config['request_timeout_seconds'] = timeout
    except ValueError:
        raise ValueError(f'{CONFIG_NAME}: [openrouter] request_timeout_seconds must be a positive number.') from None
    config['trigger_key'] = parser.get('trigger', 'key', fallback='alt').strip().lower()
    config['trigger_joystick_button'] = {
        'joystick_id': _device_id(parser, 'trigger', 'joystick_id'),
        'button': _device_id(parser, 'trigger', 'joystick_button'),
    }
    joystick = config['trigger_joystick_button']
    if (joystick['joystick_id'] is None) != (joystick['button'] is None):
        raise ValueError(f'{CONFIG_NAME}: set both joystick_id and joystick_button, or leave both blank.')
    config['audio_record_device_id'] = _device_id(parser, 'audio', 'record_device_id')
    config['audio_playback_device_id'] = _device_id(parser, 'audio', 'playback_device_id')
    config['commands'] = dict(parser['commands']) if parser.has_section('commands') else default_commands()
    from commands import command_specs
    command_specs(config['commands'])
    return config


def validate_api_config(config):
    key = os.environ.get('OPENROUTER_API_KEY') or config.get('openrouter_api_key')
    if not isinstance(key, str) or not key.strip() or key.startswith('Insert '):
        raise ValueError(f'Set OPENROUTER_API_KEY or api_key in the [openrouter] section of {CONFIG_NAME}.')
    for field in ('speech_to_text_model', 'generation_model'):
        model = config.get(field)
        if not isinstance(model, str) or '/' not in model or not model.strip():
            raise ValueError(f'{field} must be a full OpenRouter model ID (provider/model).')
    timeout = config.get('request_timeout_seconds', 30)
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError('request_timeout_seconds must be a positive number.')
    return key.strip()
