import base64
import contextlib
import io
import json
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import wave

import requests
from SimConnect import AircraftEvents

from commands import (Command, available_commands, catalog, command_ids,
                      command_prompt, decode_command, encode_command, response_format)
from generate_catalog import EXCLUDED, Tables, argument_metadata
from open_router import get_command, normalize_transcript
from record_audio import AudioRecorder
from settings import DEFAULTS, application_directory, load_config, validate_api_config
from voice_sim import execute_command
import voice_sim


def response(data):
    result = Mock()
    result.json.return_value = data
    return result


def command_json(event=None, argument=None):
    command_id = available_commands()[event]['id'] if event else None
    return json.dumps({'command_id': command_id, 'argument': argument})


def completion(content, finish='stop'):
    return response({'choices': [{'finish_reason': finish, 'message': {'content': content}}]})


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
    def test_separate_models_audio_and_structured_output_contract(self, post):
        post.side_effect = [response({'text': 'Set heading to forty five.'}), completion(command_json('HEADING_BUG_SET', 45))]
        self.assertEqual(get_command(io.BytesIO(b'WAV bytes'), self.config), Command('HEADING_BUG_SET', 45))
        stt, generation = post.call_args_list
        self.assertEqual(stt.args[0], 'https://openrouter.ai/api/v1/audio/transcriptions')
        self.assertEqual(stt.kwargs['json']['model'], 'example/transcribe')
        self.assertEqual(base64.b64decode(stt.kwargs['json']['input_audio']['data']), b'WAV bytes')
        self.assertEqual(stt.kwargs['json']['input_audio']['format'], 'wav')
        self.assertEqual(stt.kwargs['json']['language'], 'en')
        self.assertEqual(stt.kwargs['headers']['Authorization'], 'Bearer test-key')
        self.assertEqual(stt.kwargs['timeout'], (10, 30))
        payload = generation.kwargs['json']
        self.assertEqual(generation.args[0], 'https://openrouter.ai/api/v1/chat/completions')
        self.assertEqual(payload['model'], 'example/generate')
        self.assertEqual(payload['messages'][0]['role'], 'system')
        self.assertEqual(payload['messages'][1]['role'], 'user')
        self.assertEqual(payload['response_format']['type'], 'json_schema')
        self.assertTrue(payload['response_format']['json_schema']['strict'])
        self.assertEqual(payload['provider'], {'require_parameters': True})
        self.assertIn('GEAR_UP', payload['messages'][0]['content'])

    @patch('open_router.requests.post')
    def test_command_configuration_cannot_change_catalog(self, post):
        self.config['commands'] = {'invented': 'UNKNOWN'}
        post.side_effect = [response({'text': 'raise gear'}), completion(command_json('GEAR_UP'))]
        self.assertEqual(get_command(io.BytesIO(b'audio'), self.config), Command('GEAR_UP'))
        self.assertNotIn('UNKNOWN', post.call_args.kwargs['json']['messages'][0]['content'])

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
    def test_rejects_bad_refused_or_truncated_generation(self, post):
        values = [completion(command_json()), completion(command_json('HEADING_BUG_SET', 4), 'length'),
                  completion('FLAPS_UP'), completion('{"command_id":99999,"argument":null}'),
                  completion(command_json('HEADING_BUG_SET')), completion(None),
                  response({'choices': []}), response({'choices': [None]}),
                  response({'choices': [{'message': {'content': command_json('FLAPS_UP')}}]}),
                  response({'choices': [{'finish_reason': 'stop', 'message': {'refusal': 'No', 'content': None}}]})]
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

    def test_spoken_radio_digits(self):
        self.assertEqual(normalize_transcript('Set NAV two to ONE ONE OH point seven five.'), 'Set NAV 2 to 110.75')
        self.assertEqual(normalize_transcript('one one niner point two five'), '119.25')


class CommandTests(unittest.TestCase):
    def test_catalog_matches_pinned_aircraft_events(self):
        events = AircraftEvents(None)
        expected = {name.decode() for group in events.list if type(group).__name__.lstrip('_') not in EXCLUDED
                    for name, *_ in group.list if re.fullmatch(rb'[A-Z][A-Z0-9_]+', name)}
        self.assertEqual(set(catalog()), expected)
        data = json.loads((Path(__file__).resolve().parents[1] / 'aircraft_commands.json').read_text(encoding='utf-8'))
        self.assertEqual(data['simconnect_version'], version('SimConnect'))
        self.assertEqual(len(command_ids()), len(available_commands()))
        for name in available_commands():
            self.assertIsNotNone(events.find(name))
        self.assertNotIn('SLEW_ON', catalog())
        self.assertNotIn('MP_CHAT', catalog())

    def test_schema_and_prompt_share_exact_allowed_commands(self):
        schema = response_format()['json_schema']['schema']
        self.assertEqual(set(schema['properties']['command_id']['enum']), {*command_ids(), None})
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['required']), {'command_id', 'argument'})
        for entry in available_commands().values():
            self.assertIn(f'{entry["id"]}|{entry["event"]}|', command_prompt())
        for name, entry in catalog().items():
            if entry['argument'] is None:
                self.assertNotIn(f'{entry["id"]}|{name}|', command_prompt())

    def test_encodings_and_signed_values(self):
        cases = [
            ('COM_RADIO_SET', Decimal('119.25'), 0x1925),
            ('NAV2_RADIO_SET', Decimal('109.7'), 0x0970),
            ('NAV1_STBY_SET', Decimal('110.25'), 0x1025),
            ('ADF_COMPLETE_SET', Decimal('350.5'), 0x00350500),
            ('XPNDR_SET', 7700, 0x7700),
            ('XPNDR_SET', 70, 0x0070),
            ('KOHLSMAN_SET', Decimal('1013.25'), 16212),
            ('AP_MACH_VAR_SET', Decimal('0.80'), 80),
            ('AP_VS_VAR_SET_ENGLISH', -500, -500),
            ('HEADING_BUG_SET', 45, 45),
            ('THROTTLE1_SET', 8192, 8192),
            ('PROP_PITCH_SET', 8192, 8192),
            ('AXIS_PROPELLER_SET', -8192, -8192),
            ('FLAPS_UP', None, None),
        ]
        for event, argument, expected in cases:
            with self.subTest(event=event):
                self.assertEqual(encode_command(Command(event, argument)), expected)

    def test_invalid_arguments(self):
        for event, argument in [('FLAPS_UP', 1), ('HEADING_BUG_SET', None), ('HEADING_BUG_SET', -1),
                                ('HEADING_BUG_SET', 361), ('HEADING_BUG_SET', 2.5), ('HEADING_BUG_SET', True),
                                ('COM_RADIO_SET', Decimal('119.255')), ('NAV1_RADIO_SET', 200),
                                ('XPNDR_SET', 7800), ('THROTTLE1_SET', 16384), ('FUEL_DUMP_SWITCH_SET', 2), ('AP_MACH_VAR_SET', Decimal('.805')),
                                ('KOHLSMAN_SET', float('nan')), ('AP_VS_VAR_SET_ENGLISH', -2 ** 31 - 1)]:
            with self.subTest(event=event, argument=argument), self.assertRaises(ValueError):
                encode_command(Command(event, argument))

    def test_json_contract_and_exact_decimal_preservation(self):
        decoded = decode_command(command_json('COM_RADIO_SET', 119.25))
        self.assertIsInstance(decoded.argument, Decimal)
        self.assertEqual(decoded, Command('COM_RADIO_SET', Decimal('119.25')))
        self.assertIsNone(decode_command(command_json()))
        invalid = ['FLAPS_UP', '{}', '[]', 'null', command_json() + command_json(),
                   '{"command_id":true,"argument":null}', '{"command_id":null,"argument":0}',
                   '{"command_id":null,"argument":NaN}', '{"command_id":null,"argument":null,"extra":1}',
                   '{"command_id":null,"argument":null,"argument":null}',
                   json.dumps({'command_id': catalog()['KEY_TUG_SPEED']['id'], 'argument': 1})]
        for content in invalid:
            with self.subTest(content=content), self.assertRaises(ValueError):
                decode_command(content)

    def test_dispatch_revalidates_before_sending(self):
        events = Mock()
        with contextlib.redirect_stdout(io.StringIO()):
            execute_command(events, Command('COM_RADIO_SET', Decimal('119.25')))
            events.find.assert_called_with('COM_RADIO_SET')
            events.find.return_value.assert_called_once_with(0x1925)
            events.find.return_value.reset_mock()
            execute_command(events, Command('FLAPS_UP'))
            events.find.return_value.assert_called_once_with()
            events.reset_mock()
            for command in (Command('UNKNOWN'), Command('HEADING_BUG_SET', 900), 'FLAPS_UP'):
                with self.assertRaises(ValueError):
                    execute_command(events, command)
            events.find.assert_not_called()

    def test_sdk_table_parser_and_metadata(self):
        parser = Tables()
        parser.feed('<table><tr><td>EVENT</td><td>[0]:<br>Bool</td><td>Toggle</td></tr></table>')
        self.assertEqual(parser.rows, [['EVENT', '[0]: Bool', 'Toggle']])
        argument, reason = argument_metadata('SOME_SET', 'Set flag', '[0]: Bool', 'Sets flag.')
        self.assertIsNone(reason)
        self.assertEqual((argument['min'], argument['max']), (0, 1))
        argument, reason = argument_metadata('SOME_SET', 'Unknown', '', 'Unknown')
        self.assertIsNone(argument)
        self.assertIn('does not specify', reason)


class RecordingTests(unittest.TestCase):
    @patch('record_audio.pyaudio.PyAudio')
    def test_finalized_wav_and_cleanup(self, audio_interface):
        recorder = AudioRecorder(3)
        interface = audio_interface.return_value
        def read(*args, **kwargs):
            recorder.stop_requested.set()
            return b'\x00\x00' * 1024
        interface.open.return_value.read.side_effect = read
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
    def test_frozen_settings_use_executable_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'VoiceSim.exe'
            with patch('settings.sys.frozen', True, create=True), patch('settings.sys.executable', str(executable)):
                self.assertEqual(application_directory(), executable.parent)

    def load_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'VoiceSim.ini').write_text(text, encoding='utf-8')
            with patch('settings.APP_DIR', root):
                return load_config()

    def test_no_command_configuration_needed(self):
        config = self.load_text('[trigger]\nkey = f9\n')
        self.assertEqual(config['trigger_key'], 'f9')
        self.assertNotIn('commands', config)
        config = self.load_text('[commands]\nobsolete example = UNKNOWN\n')
        self.assertNotIn('commands', config)

    def test_setup_preserves_user_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('settings.APP_DIR', root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(load_config()['trigger_key'], 'alt')
                path = root / 'VoiceSim.ini'
                self.assertNotIn('[commands]', path.read_text(encoding='utf-8'))
                path.write_text('[trigger]\nkey = f9\n', encoding='utf-8')
                self.assertEqual(load_config()['trigger_key'], 'f9')

    def test_plain_values_comments_and_optional_fields(self):
        config = self.load_text('''# comment
[openrouter]
api_key = literal%value#not-an-inline-comment;either
speech_language = en
request_timeout_seconds = 45.5
[trigger]
key = F8
joystick_id = 0
joystick_button = 2
[audio]
record_device_id = 3
playback_device_id =
''')
        self.assertEqual(config['openrouter_api_key'], 'literal%value#not-an-inline-comment;either')
        self.assertEqual(config['speech_language'], 'en')
        self.assertEqual(config['request_timeout_seconds'], 45.5)
        self.assertEqual(config['trigger_key'], 'f8')
        self.assertEqual(config['trigger_joystick_button'], {'joystick_id': 0, 'button': 2})
        self.assertEqual(config['audio_record_device_id'], 3)
        self.assertIsNone(config['audio_playback_device_id'])

    def test_bad_config_reports_actionable_error(self):
        for text, message in [('[openrouter]\nrequest_timeout_seconds = nope', 'positive number'),
                              ('[openrouter]\nrequest_timeout_seconds = nan', 'positive number'),
                              ('[audio]\nrecord_device_id = -1', 'non-negative integer'),
                              ('[audio]\nrecord_device_id = 1.5', 'non-negative integer'),
                              ('[trigger]\njoystick_id = 0', 'both joystick_id'),
                              ('[wrong]\nkey = alt', 'unknown section'),
                              ('[openrouter]\ngeneration_modle = provider/model', 'unknown setting'),
                              ('[DEFAULT]\nkey = alt', 'DEFAULT')]:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, message):
                self.load_text(text)

    def test_parse_error_does_not_expose_key(self):
        with self.assertRaises(ValueError) as caught:
            self.load_text('[openrouter]\nprivate-test-key-without-equals\n')
        self.assertIn('line 2', str(caught.exception))
        self.assertNotIn('private-test-key', str(caught.exception))


class CliTests(unittest.TestCase):
    def test_helpers_do_not_load_config_or_connect(self):
        for option, function, parameter in [(['--list-audio-devices'], 'device_tools.list_audio_devices', None),
                                             (['--list-joysticks'], 'device_tools.list_joysticks', None),
                                             (['--list-joystick-buttons', '0'], 'device_tools.list_joystick_buttons', 0),
                                             (['--list-commands'], 'voice_sim.list_commands', None)]:
            with self.subTest(option=option), patch(function) as helper, patch('voice_sim.main') as main, patch('voice_sim.load_config') as config:
                self.assertEqual(voice_sim.cli(option), 0)
                helper.assert_called_once_with(*(() if parameter is None else (parameter,)))
                main.assert_not_called()
                config.assert_not_called()

    def test_startup_error_returns_failure(self):
        with patch('voice_sim.main', side_effect=ValueError('Missing API key')), contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(voice_sim.cli([]), 1)
            self.assertIn('Missing API key', output.getvalue())


class TriggerTests(unittest.TestCase):
    def run_main(self, config, modules):
        patches = [patch('voice_sim.load_config', return_value={**DEFAULTS, **config, 'openrouter_api_key': 'test-key'}),
                   patch('voice_sim.SimConnect'), patch('voice_sim.AircraftEvents'),
                   patch('voice_sim.AudioRecorder'), patch('voice_sim.AudioNotifier'),
                   patch('voice_sim.get_command', return_value=Command('FLAPS_UP')),
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
        keyboard.read_event.side_effect = [SimpleNamespace(name='alt', event_type=kind)
                                         for kind in ('up', 'down', 'down', 'up')] + [KeyboardInterrupt()]
        self.run_main({}, {'keyboard': keyboard})

    def test_joystick_filters_other_devices(self):
        pygame = Mock(JOYBUTTONDOWN=1, JOYBUTTONUP=2)
        joystick = pygame.joystick.Joystick.return_value
        joystick.get_instance_id.return_value = 7
        joystick.get_numbuttons.return_value = 4
        pygame.event.get.side_effect = [[Mock(type=1, instance_id=8, button=2), Mock(type=2, instance_id=8, button=2),
                                         Mock(type=1, instance_id=7, button=2), Mock(type=2, instance_id=7, button=2)], KeyboardInterrupt()]
        self.run_main({'trigger_joystick_button': {'joystick_id': 0, 'button': 2}}, {'pygame': pygame})
        pygame.quit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
