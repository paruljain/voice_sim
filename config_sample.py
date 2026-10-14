# Copy to config.py. OPENROUTER_API_KEY in the environment takes precedence.
config = {
    'trigger_key': 'alt',
    'trigger_joystick_button': {
        'joystick_id': None,
        'button': None,
    },
    'openrouter_api_key': '',
    # Transcription: openai/whisper-large-v3, openai/gpt-4o-mini-transcribe,
    # mistralai/voxtral-mini-transcribe (not general audio chat models).
    'speech_to_text_model': 'openai/whisper-large-v3',
    # Generation: openai/gpt-4.1-mini, google/gemini-2.5-flash
    'generation_model': 'openai/gpt-4.1-mini',
    # None auto-detects the language; use 'en' to force English.
    'speech_language': None,
    'request_timeout_seconds': 30,
    'audio_playback_device_id': None,
    'audio_record_device_id': None,
}
