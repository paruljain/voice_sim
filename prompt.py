prompt = '''Convert text to command by using the following lookup table:

Text: Command
turn on autopilot: AUTOPILOT_ON
turn off autopilot: AUTOPILOT_OFF
autopilot altitude hold on: AP_PANEL_ALTITUDE_ON
autopilot altitude hold off: AP_PANEL_ALTITUDE_OFF
autopilot heading hold on: AP_HDG_HOLD_ON
autopilot heading hold off: AP_HDG_HOLD_OFF
autopilot nav1 hold on: AP_NAV1_HOLD_ON
autopilot nav1 hold off: AP_NAV1_HOLD_OFF
toggle parking brake or brakes: PARKING_BRAKES
increase flap or increase flaps: FLAPS_INCR
decrease flap or decrease flaps: FLAPS_DECR
flap or flaps up: FLAPS_UP
flap or flaps down: FLAPS_DOWN
toggle landing light or lights: LANDING_LIGHTS_TOGGLE
toggle strobe light or lights: STROBES_TOGGLE
toggle panel light or lights: PANEL_LIGHTS_TOGGLE
toggle taxi light or lights: TOGGLE_TAXI_LIGHTS
toggle cabin light or lights: TOGGLE_CABIN_LIGHTS
autopilot heading hold on: AP_HDG_HOLD_ON
set heading to 25 degrees: HEADING_BUG_SET,25
set autopilot altitude to 20000 feet: AP_ALT_VAR_ENGLISH,20000
set autopilot vertical speed to 500: AP_VS_VAR_SET_ENGLISH,500
set autopilot vertical speed to minus 500: AP_VS_VAR_SET_ENGLISH,-500
set autopilot vertical speed to 0: AP_VS_VAR_SET_ENGLISH,0
set comm or com radio to 125.95: COM_RADIO_SET,125.95
set nav1 radio to 110.25: NAV1_RADIO_SET,110.25
set nav radio 1 to 110.25: NAV1_RADIO_SET,110.25
set nav2 radio to 109.70: NAV2_RADIO_SET,109.70
set nav radio 2 to 109.70: NAV2_RADIO_SET,109.70
'''