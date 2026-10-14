"""Validate generated commands before sending them to SimConnect."""
from decimal import Decimal, InvalidOperation
import re

import prompt


def command_specs():
    specs = {}
    for line in prompt.get_prompt().splitlines():
        if ': ' not in line:
            continue
        example = line.split(': ', 1)[1].strip()
        if re.fullmatch(r'[A-Z][A-Z0-9_]*(?:,-?\d+(?:\.\d+)?)?', example):
            name, *parameter = example.split(',')
            specs[name] = bool(parameter)
    return specs


def parse_command(text):
    """Return (event, parameter), or None for the explicit no-command response."""
    if not isinstance(text, str):
        raise ValueError('Expected a text command.')
    text = text.strip()
    if text == 'NONE':
        return None
    match = re.fullmatch(r'([A-Z][A-Z0-9_]*)(?:\s*,\s*(-?\d+(?:\.\d+)?))?', text)
    if not match:
        raise ValueError('Expected one SimConnect event, optionally followed by a number.')
    name, value = match.groups()
    specs = command_specs()
    if name not in specs:
        raise ValueError(f'Command is not in the command table: {name}')
    if specs[name] != (value is not None):
        raise ValueError(f'Incorrect parameter count for {name}.')
    if value is None:
        return name, None
    if name.endswith('_RADIO_SET'):
        try:
            frequency = Decimal(value)
            lower, upper = (Decimal('118'), Decimal('137')) if name.startswith('COM') else (Decimal('108'), Decimal('118'))
            if not lower <= frequency < upper or frequency != frequency.quantize(Decimal('0.01')):
                raise ValueError('Radio frequency is outside its range or has more than two decimals.')
            # Legacy radio events expect the last four digits in BCD.
            parameter = int(f'{int(frequency * 100) % 10000:04d}', 16)
        except InvalidOperation as exc:
            raise ValueError('Invalid radio frequency.') from exc
    else:
        if '.' in value:
            raise ValueError(f'{name} requires an integer parameter.')
        parameter = int(value)
        if not -(2 ** 31) <= parameter < 2 ** 32:
            raise ValueError('Parameter does not fit a SimConnect 32-bit value.')
    return name, parameter
