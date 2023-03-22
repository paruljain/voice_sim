import requests
from config import config
import prompt as base_prompt

def getCommand(audio_file):
    url = 'https://api.openai.com/v1/audio/translations'
    headers = {
        'Authorization': f'Bearer {config["open_ai_api_key"]}'
    }
    data = {'model': 'whisper-1'}
    
    files = {'file': ('audio_file.wav', audio_file.read(), 'audio/wav')}

    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=5)
    except:
        print('Timed out waiting for Whisper to respond')
        return

    text = None
    if response.ok:
        text = response.json()['text']
    else:
        print(f'Whisper error: {response.status_code}: {response.text}')
        return

    # Sometimes Whisper will translate radio frequencies to text like so
    # one one three point nine zero
    # This confuses GPT. We need to convert these words to numerals
    numbers = {
        'zero': '0',
        'one': '1',
        'two': '2',
        'three': '3',
        'four': '4',
        'five': '5',
        'six': '6',
        'seven': '7',
        'eight': '8',
        'nine': '9',
        'niner': '9',
        'point': '.'
    }
    # Remove any trailing period from Whisper text
    if text.endswith('.'):
        text = text[:-1]
    newText = ''
    for token in text.split(' '):
        if token in numbers:
            newText += numbers[token]
        else:
            newText += token + ' '
    
    text = newText.strip()
    print(f'Whisper: {text}')

    prompt = base_prompt.prompt + text + ':'
    
    url = 'https://api.openai.com/v1/completions'
    headers = {
        'Authorization': f'Bearer {config["open_ai_api_key"]}'
    }
    payload = {
        'model': "text-babbage-001",
        'prompt': prompt,
        'temperature': 0,
        'max_tokens': 20,
        'top_p': 1.0,
        'n': 1,
        'frequency_penalty': 0.0,
        'presence_penalty': 0.0,
        'stop': '\n'
    }
    cmd = None
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
    except:
        print('Timed out waiting for GPT-3 to respond')
        return
    
    if response.ok and len(response.json()['choices']) > 0:
        cmd = response.json()['choices'][0]['text'].strip()
        print(f'GPT-3: {cmd}')
    else:
        print(f'GPT-3 error: {response.status_code}: {response.text}')
    return cmd
