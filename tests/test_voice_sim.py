import base64
import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import requests

from commands import command_specs, parse_command
from open_router import get_command, normalize_transcript
from record_audio import AudioRecorder
from settings import DEFAULTS, load_config, validate_api_config
from voice_sim import execute_command
import voice_sim
from SimConnect import AircraftEvents


def response(data):
    result = Mock()
    result.json.return_value = data
    return result


def completion(command, finish='stop'):
    return response({'choices': [{'finish_reason': finish, 'message': {'content': command}}]})


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.config = {**DEFAULTS, 'openrouter_api_key': 'test-key',
                       'speech_to_text_model': 'example/transcribe',
                       'generation_model': 'example/generate', 'speech_language': 'en'}
        self.env = patch.dict('os.environ', {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    @patch('open_router.requests.post')
    def test_separate_models_and_audio_contract(self, post):
        post.side_effect = [response({'text': 'Set heading to forty five.'}), completion('HEADING_BUG_SET,45')]
        self.assertEqual(get_command(io.BytesIO(b'WAV bytes'), self.config), 'HEADING_BUG_SET,45')
        stt, generation = post.call_args_list
        self.assertEqual(stt.args[0], 'https://openrouter.ai/api/v1/audio/transcriptions')
        self.assertEqual(stt.kwargs['json']['model'], 'example/transcribe')
        self.assertEqual(base64.b64decode(stt.kwargs['json']['input_audio']['data']), b'WAV bytes')
        self.assertEqual(stt.kwargs['json']['input_audio']['format'], 'wav')
        self.assertEqual(stt.kwargs['json']['language'], 'en')
        self.assertEqual(stt.kwargs['headers']['Authorization'], 'Bearer test-key')
        self.assertEqual(stt.kwargs['timeout'], (10, 30))
        self.assertEqual(generation.args[0], 'https://openrouter.ai/api/v1/chat/completions')
        self.assertEqual(generation.kwargs['json']['model'], 'example/generate')
        self.assertEqual(generation.kwargs['json']['messages'][0]['role'], 'system')
        self.assertEqual(generation.kwargs['json']['messages'][1]['role'], 'user')

    @patch('open_router.requests.post')
    def test_transcription_failures_do_not_generate(self, post):
        for value in ({'text': ''}, {'text': None}, {}, {'error': {'message': 'failure'}}, []):
            with self.subTest(value=value):
                post.reset_mock()
                post.return_value = response(value)
                self.assertIsNone(get_command(io.BytesIO(b'audio'), self.config))
                post.assert_called_once()
        for error in (requests.Timeout(), requests.ConnectionError(), ValueError('bad JSON')):
            with self.subTest(error=error):
                post.reset_mock()
                post.side_effect = error
                self.assertIsNone(get_command(io.BytesIO(b'audio'), self.config))
                post.assert_called_once()

    @patch('open_router.requests.post')
    def test_http_errors_do_not_generate(self, post):
        for status in (401, 402, 404, 429, 500):
            with self.subTest(status=status):
                failed = response({})
                failed.status_code = status
                failed.raise_for_status.side_effect = requests.HTTPError(response=failed)
                post.reset_mock()
                post.return_value = failed
                self.assertIsNone(get_command(io.BytesIO(b'audio'), self.config))
                post.assert_called_once()

    @patch('open_router.requests.post')
    def test_rejects_bad_or_truncated_generation(self, post):
        values = [completion('NONE'), completion('HEADING_BUG_SET,4', 'length'),
                  completion('FLAPS_UP\nPARKING_BRAKES'), completion('UNKNOWN'),
                  completion('HEADING_BUG_SET'), completion(None),
                  response({'choices': []}), response({'choices': [None]}),
                  response({'choices': [{'message': {'content': 'FLAPS_UP'}}]})]
        for value in values:
            with self.subTest(value=value):
                post.side_effect = [response({'text': 'flaps up'}), value]
                self.assertIsNone(get_command(io.BytesIO(b'audio'), self.config))

    @patch('open_router.requests.post')
    def test_empty_audio_has_no_request(self, post):
        self.assertIsNone(get_command(io.BytesIO(), self.config))
        post.assert_not_called()

    def test_environment_key_and_invalid_settings(self):
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'environment-key'}):
            self.assertEqual(validate_api_config(self.config), 'environment-key')
        for field, value in [('openrouter_api_key', ''), ('speech_to_text_model', 'whisper-1'),
                             ('generation_model', None), ('request_timeout_seconds', 0),
                             ('request_timeout_seconds', float('nan'))]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_api_config({**self.config, field: value})
        with self.assertRaisesRegex(ValueError, 'Set OPENROUTER_API_KEY'):
            validate_api_config(DEFAULTS)

    def test_spoken_radio_digits(self):
        self.assertEqual(normalize_transcript('Set NAV two to ONE ONE OH point seven five.'), 'Set NAV 2 to 110.75')
        self.assertEqual(normalize_transcript('one one niner point two five'), '119.25')


class CommandTests(unittest.TestCase):
    def test_prompt_events_exist_in_installed_simconnect(self):
        events = AircraftEvents(Mock())
        for name in command_specs():
            with self.subTest(name=name):
                self.assertIsNotNone(events.find(name))

    def test_radio_bcd_and_integer_parameters(self):
        self.assertEqual(parse_command('COM_RADIO_SET,119.25'), ('COM_RADIO_SET', 0x1925))
        self.assertEqual(parse_command('NAV2_RADIO_SET,109.7'), ('NAV2_RADIO_SET', 0x0970))
        self.assertEqual(parse_command('AP_VS_VAR_SET_ENGLISH,-500'), ('AP_VS_VAR_SET_ENGLISH', -500))
        self.assertEqual(parse_command('HEADING_BUG_SET, 45'), ('HEADING_BUG_SET', 45))
        self.assertEqual(parse_command('FLAPS_UP'), ('FLAPS_UP', None))

    def test_invalid_commands(self):
        for command in ('FLAPS_UP,1', 'UNKNOWN', 'HEADING_BUG_SET', 'HEADING_BUG_SET,2.5',
                        'FLAPS_UP\nFLAPS_DOWN', '```FLAPS_UP```', 'NAV1_RADIO_SET,200.00',
                        'COM_RADIO_SET,119.255', 'HEADING_BUG_SET,9999999999999999'):
            with self.subTest(command=command), self.assertRaises(ValueError):
                parse_command(command)

    def test_dispatch(self):
        events = Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            execute_command(events, 'COM_RADIO_SET,119.25')
            events.find.assert_called_with('COM_RADIO_SET')
            events.find.return_value.assert_called_once_with(0x1925)
            events.find.return_value.reset_mock()
            execute_command(events, 'FLAPS_UP')
            events.find.return_value.assert_called_once_with()
            events.reset_mock()
            with self.assertRaises(ValueError):
                execute_command(events, 'UNKNOWN')
            events.find.assert_not_called()


class RecordingTests(unittest.TestCase):
    @patch('record_audio.pyaudio.PyAudio')
    def test_finalized_wav_and_cleanup(self, audio_interface):
        recorder = AudioRecorder(3)
        interface = audio_interface.return_value
        def read(*args, **kwargs):
            recorder.stop_requested.set()
            return b'\x00\x00' * 1024
        interface.open.return_value.read.side_effect = read
        # Wait for the fake read instead of racing stop against thread startup.
        recorder.start()
        recorder.thread.join(timeout=2)
        with recorder.stop() as audio:
            with wave.open(audio, 'rb') as wav:
                self.assertEqual(wav.getframerate(), 16000)
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getnframes(), 1024)
                self.assertEqual(len(wav.readframes(1024)), 2048)
        interface.open.return_value.close.assert_called_once()
        interface.terminate.assert_called_once()

    @patch('record_audio.pyaudio.PyAudio')
    def test_device_failure_completes_and_can_restart(self, audio_interface):
        audio_interface.return_value.open.side_effect = OSError('No microphone')
        recorder = AudioRecorder()
        for _ in range(2):
            recorder.start()
            with self.assertRaisesRegex(RuntimeError, 'Could not record'):
                recorder.stop()
            self.assertIsNone(recorder.thread)
        self.assertEqual(audio_interface.return_value.terminate.call_count, 2)


class SettingsTests(unittest.TestCase):
    def test_copy_sample_without_overwriting_and_load_from_app_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / 'config_sample.py'
            sample.write_text("config = {'trigger_key': 'f8'}\n", encoding='utf-8')
            with patch('settings.APP_DIR', root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(load_config()['trigger_key'], 'f8')
                self.assertTrue(sample.exists())
                (root / 'config.py').write_text("config = {'trigger_key': 'f9'}\n", encoding='utf-8')
                self.assertEqual(load_config()['trigger_key'], 'f9')


class TriggerTests(unittest.TestCase):
    def run_main(self, config, modules):
        patches = [patch('voice_sim.load_config', return_value={**DEFAULTS, **config, 'openrouter_api_key': 'test-key'}),
                   patch('voice_sim.SimConnect'), patch('voice_sim.AircraftEvents'),
                   patch('voice_sim.AudioRecorder'), patch('voice_sim.AudioNotifier'),
                   patch('voice_sim.get_command', return_value='FLAPS_UP'),
                   patch.dict('sys.modules', modules)]
        with contextlib.ExitStack() as stack:
            mocks = [stack.enter_context(p) for p in patches]
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            recorder = mocks[3].return_value
            recorder.stop.return_value = io.BytesIO(b'0' * 100)
            voice_sim.main()
            recorder.start.assert_called_once()
            recorder.stop.assert_called_once()
            mocks[4].return_value.notify.assert_called_once()
            mocks[2].return_value.find.assert_called_once_with('FLAPS_UP')
            mocks[1].return_value.exit.assert_called_once()
            mocks[4].return_value.close.assert_called_once()
            recorder.close.assert_called_once()

    def test_keyboard_ignores_repeat_and_unmatched_release(self):
        keyboard = Mock(KEY_DOWN='down', KEY_UP='up')
        keyboard.read_event.side_effect = [
            SimpleNamespace(name='alt', event_type='up'),
            SimpleNamespace(name='alt', event_type='down'),
            SimpleNamespace(name='alt', event_type='down'),
            SimpleNamespace(name='alt', event_type='up'),
            KeyboardInterrupt(),
        ]
        self.run_main({}, {'keyboard': keyboard})

    def test_joystick_filters_other_devices(self):
        pygame = Mock(JOYBUTTONDOWN=1, JOYBUTTONUP=2)
        joystick = pygame.joystick.Joystick.return_value
        joystick.get_instance_id.return_value = 7
        joystick.get_numbuttons.return_value = 4
        pygame.event.get.side_effect = [[
            Mock(type=1, instance_id=8, button=2),
            Mock(type=2, instance_id=8, button=2),
            Mock(type=1, instance_id=7, button=2),
            Mock(type=2, instance_id=7, button=2),
        ], KeyboardInterrupt()]
        self.run_main({'trigger_joystick_button': {'joystick_id': 0, 'button': 2}}, {'pygame': pygame})
        pygame.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
