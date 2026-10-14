"""Regenerate the bundled aircraft catalog from the pinned package and SDK tables.

Run this developer tool on Windows with the runtime requirements installed.
Network access is needed here, never at application startup.
"""
import hashlib
from html.parser import HTMLParser
from importlib.metadata import version
import json
from pathlib import Path
import re
from urllib.request import urlopen

from SimConnect import AircraftEvents

ROOT = Path(__file__).resolve().parent
EXCLUDED = {'Failures', 'Slew_System', 'View_System', 'Miscellaneous_Events',
            'Freezing_position', 'Mission_Keys', 'ATC', 'Multiplayer'}
PAGES = ['Aircraft_Autopilot_Flight_Assist_Events', 'Aircraft_Electrical_Events',
         'Aircraft_Engine_Events', 'Aircraft_Flight_Control_Events',
         'Aircraft_Fuel_System_Events', 'Aircraft_Instrumentation_Events',
         'Aircraft_Misc_Events', 'Aircraft_Radio_Navigation_Events', 'Helicopter_Specific_Events']
SDK_BASE = 'https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/'


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = []
        elif tag == 'br' and self.cell is not None:
            self.cell.append(' ')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def package_events():
    rows = {}
    for group in AircraftEvents(None).list:
        category = type(group).__name__.lstrip('_')
        if category in EXCLUDED:
            continue
        for name, description, *_ in group.list:
            name = name.decode()
            if re.fullmatch(r'[A-Z][A-Z0-9_]+', name):
                rows[name] = {'event': name, 'category': category,
                              'description': ' '.join(description.split()).rstrip(',')}
    return rows


def argument_metadata(name, description, parameters, sdk_description):
    """Only enable documented scalar DWORD events or explicit legacy defaults."""
    combined = parameters + ' ' + sdk_description
    # These legacy events accept the first value with the default simulator
    # selector through TransmitClientEvent. Explicit additional indexes are not
    # exposed by this wrapper; they must never be inferred from a user's speech.
    default_selector = '[1]' in parameters
    if re.search(r'not (?:currently )?used|no longer used|not supported|deprecated', sdk_description, re.I):
        return None, 'SDK marks this event obsolete or unsupported.'
    if name == 'MIXTURE_SET_BEST' or name == 'HEADING_GYRO_SET':
        return {'type': 'none'}, None
    known_legacy_set = re.fullmatch(r'(?:AXIS_)?(?:THROTTLE|MIXTURE)\d?_SET|(?:AXIS_)?FLAPS_SET|PROP_PITCH\d?_SET|AXIS_PROPELLER\d?_SET', name)
    legacy_selector = name.startswith('FUEL_SELECTOR') and name.endswith('_SET')
    needs_argument = bool(parameters and parameters != 'N/A') or bool(known_legacy_set or legacy_selector)
    if not parameters and name.endswith('_SET') and not needs_argument:
        if name in {'FUEL_DUMP_SWITCH_SET', 'HOIST_SWITCH_SET', 'HOIST_DEPLOY_SET'}:
            needs_argument = True
        else:
            return None, 'SDK does not specify the argument contract for this setter.'
    if not needs_argument:
        return {'type': 'none'}, None
    meta = {'type': 'integer', 'min': 0, 'max': 4294967295, 'encoding': 'identity',
            'unit': re.split(r'\[1\]', parameters)[0].replace('[0]', '').lstrip(': ').strip() or 'SimConnect integer'}
    if meta['unit'] == 'N/A':
        meta['unit'] = 'SimConnect integer'
    if default_selector:
        meta['default_selector_only'] = True
    primary = re.split(r'\[1\]', parameters)[0]
    range_pattern = r'(?<![\w.])(-?\d+)\s*(?:to|[-\u2013])\s*\+?(-?\d+)(?![\w.])'
    bounds = re.search(range_pattern, primary) or re.search(range_pattern, description)
    if bounds:
        low, high = map(int, bounds.groups())
        if low <= high:
            meta.update(min=low, max=high)
    if re.search(r'bool|TRUE\s*(?:/|or)\s*FALSE|\(0,\s*1\)|\(1,\s*0\)|either on \(1\) or off \(0\)', primary + ' ' + description, re.I):
        meta.update(min=0, max=1, unit='0 off / 1 on')
    if legacy_selector:
        meta.update(min=0, max=18, unit='fuel selector code: 0 off, 1 all, 2 left, 3 right, 4 left aux, 5 right aux, 6 center, 16 both, 18 isolate; other codes in FUEL_SELECTOR_SET description')
    if name == 'HOIST_SWITCH_SET':
        meta.update(min=-2147483648, max=2147483647, unit='negative up / 0 off / positive down')
    if name == 'HOIST_DEPLOY_SET':
        meta.update(min=0, max=1, unit='0 retract / 1 extend')
    if name in {'HEADING_BUG_SET', 'ADF_CARD_SET'}:
        meta.update(min=0, max=360, unit='degrees')
    if name in {'AP_ALT_VAR_SET_ENGLISH', 'AP_ALT_VAR_SET_METRIC', 'AP_SPD_VAR_SET'}:
        meta['unit'] = {'AP_ALT_VAR_SET_ENGLISH': 'feet', 'AP_ALT_VAR_SET_METRIC': 'meters', 'AP_SPD_VAR_SET': 'knots'}[name]
    if name in {'AP_VS_VAR_SET_ENGLISH', 'AP_VS_VAR_SET_METRIC'}:
        meta.update(min=-2147483648, max=2147483647,
                    unit='feet per minute' if name.endswith('ENGLISH') else 'meters per minute')
    if name == 'AP_MACH_VAR_SET':
        meta.update(type='number', min=0, max=42949672.95, encoding='mach100', unit='Mach (two decimal places)')
    if name == 'KOHLSMAN_SET':
        meta.update(type='number', min=0, max=268435455.9375, encoding='pressure16', unit='hPa / millibars')
    if name == 'XPNDR_SET':
        meta.update(min=0, max=7777, encoding='transponder_bcd', unit='four-digit squawk, digits 0 through 7')
    if re.fullmatch(r'(?:COM\d?|NAV\d)_?(?:STBY_)?RADIO_SET|NAV[12]_STBY_SET', name):
        com = name.startswith('COM')
        meta.update(type='number', min=118 if com else 108, max=136.99 if com else 117.99,
                    encoding='radio_bcd', unit='MHz (at most two decimal places)')
    elif name in {'ADF_COMPLETE_SET', 'ADF2_COMPLETE_SET', 'ADF_SET', 'ADF2_SET'}:
        meta.update(type='number', min=190, max=1799.9, encoding='adf_bcd', unit='kHz (one decimal place)')
    elif 'BCD' in combined.upper() and meta['encoding'] == 'identity':
        return None, 'This event requires an encoding that is not implemented.'
    if re.search(r'float|radians|pointer|string', primary, re.I) and meta['encoding'] == 'identity':
        return None, 'This event requires a non-integer transport that is not implemented.'
    return meta, None


def main():
    documentation = {}
    sources = []
    for page in PAGES:
        url = SDK_BASE + page + '.htm'
        raw = urlopen(url, timeout=30).read()
        parser = Tables()
        parser.feed(raw.decode('utf-8', errors='replace'))
        sources.append({'url': url, 'sha256': hashlib.sha256(raw).hexdigest()})
        for row in parser.rows:
            if len(row) != 3:
                continue
            for name in re.findall(r'\b[A-Z][A-Z0-9_]+\b', row[0]):
                documentation[name] = (row[1], row[2], url)
    events = package_events()
    for command_id, name in enumerate(sorted(events), 1):
        entry = events[name]
        entry['id'] = command_id
        if name not in documentation:
            entry.update(argument=None, unavailable_reason='Not found in the MSFS SDK event documentation.')
            continue
        parameters, sdk_description, url = documentation[name]
        argument, reason = argument_metadata(name, entry['description'], parameters, sdk_description)
        entry.update(argument=argument, sdk_source=url)
        if reason:
            entry['unavailable_reason'] = reason
    result = {
        'format_version': 1,
        'simconnect_version': version('SimConnect'),
        'source': 'https://github.com/odwdinc/Python-SimConnect/blob/master/SimConnect/EventList.py',
        'excluded_categories': sorted(EXCLUDED),
        'sdk_sources': sources,
        'commands': list(events[name] for name in sorted(events)),
    }
    (ROOT / 'aircraft_commands.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    enabled = sum(entry['argument'] is not None for entry in events.values())
    print(f'Generated {len(events)} aircraft entries; {enabled} executable, {len(events) - enabled} unavailable.')


if __name__ == '__main__':
    main()
