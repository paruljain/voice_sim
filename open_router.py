"""Speech transcription and command generation through OpenRouter."""
import base64
import re

import requests

from commands import command_prompt, decode_command, response_format
from settings import load_config, validate_api_config

BASE_URL = 'https://openrouter.ai/api/v1'


def normalize_transcript(text):
    numbers = dict(zip(
        ('zero', 'oh', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'niner', 'point'),
        ('0', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '9', '.'),
    ))
    # Join runs of spoken digits; leave e.g. "twenty five" to the model.
    pattern = r'\b(?:' + '|'.join(numbers) + r')\b(?:[\s-]+\b(?:' + '|'.join(numbers) + r')\b)*'
    return re.sub(pattern, lambda m: ''.join(numbers[word.lower()] for word in re.split(r'[\s-]+', m.group())),
                  text.strip().rstrip('.'), flags=re.IGNORECASE)


def _request(endpoint, payload, config, key, stage):
    try:
        response = requests.post(
            f'{BASE_URL}/{endpoint}',
            headers={'Authorization': f'Bearer {key}', 'X-OpenRouter-Title': 'VoiceSim'},
            json=payload,
            timeout=(10, config.get('request_timeout_seconds', 30)),
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get('error'):
            raise ValueError('OpenRouter returned an error or an invalid response.')
        return data
    except requests.Timeout:
        print(f'{stage} timed out. Try again or increase request_timeout_seconds.')
    except requests.HTTPError as exc:
        status = exc.response.status_code
        hint = {401: 'Check your OpenRouter API key.', 402: 'Check your OpenRouter credits.',
                404: 'Check the configured model ID.', 429: 'Rate limited; try again later.'}.get(status, 'Check model support and OpenRouter status.')
        print(f'{stage} failed (HTTP {status}). {hint}')
    except requests.RequestException:
        print(f'{stage} failed to connect to OpenRouter. Check your network.')
    except ValueError:
        print(f'{stage} returned an invalid response.')
    return None


def get_command(audio_file, config=None):
    config = load_config() if config is None else config
    key = validate_api_config(config)
    audio = audio_file.read()
    if not audio:
        return None
    payload = {
        'model': config['speech_to_text_model'],
        'input_audio': {'data': base64.b64encode(audio).decode('ascii'), 'format': 'wav'},
    }
    if config.get('speech_language'):
        payload['language'] = config['speech_language']
    data = _request('audio/transcriptions', payload, config, key, 'Speech-to-text')
    if data is None:
        return None
    text = data.get('text')
    if not isinstance(text, str) or not text.strip():
        print('Speech-to-text returned no transcript.')
        return None
    text = normalize_transcript(text)
    if not text:
        return None
    print(f'Transcript: {text}')
    data = _request('chat/completions', {
        'model': config['generation_model'],
        'messages': [
            {'role': 'system', 'content': command_prompt()},
            {'role': 'user', 'content': text},
        ],
        'temperature': 0,
        'max_tokens': 128,
        'response_format': response_format(),
        'provider': {'require_parameters': True},
    }, config, key, 'Command generation')
    if data is None:
        return None
    try:
        choice = data['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError('Generation did not finish normally.')
        command = decode_command(choice['message']['content'])
        if command is None:
            print('No supported command recognized.')
            return None
        print(f'Command: {command.event}; argument: {command.argument}')
        return command
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        print(f'Ignored invalid generated command: {exc}')
        return None
