## Introduction
VoiceSim allows Microsoft Flight Simulator (MSFS) players to reliably operate aircraft controls with speech. The project is especially useful for VR players because they cannot see the keyboard, mouse, joystick and other controllers. The project is written in Python and uses OpenAI API "Whisper" for speech to text, and "GPT-3" (same technology as ChatGPT) for generating flight simulator SIMCONNECT commands.

You can say things like:
* Set comm radio to one one niner point two five
* Set nav radio two to one one o point seven five
* Flaps increase
* Increase flaps
* Toggle landing lights
* Toggle parking brake (or brakes)
* Autopilot heading hold on
* Set heading to forty five degrees
* Heading to forty five
* Set autopilot vertical speed to minus five hundred feet per minute
* Set autopilot vertical speed to minus five hundred
* Autopilot vertical speed minus five hundred

## Prerequisites
* MSFS 2020
May work with FSX SP2; tested only with MSFS 2020
* Windows 11
May work on older versions; tested only on Windows 11
* Python 3
* PIP
* A microphone
* Speakers or headset
* API key from OpenAI. You can [get one here](https://platform.openai.com/playground) for free. Sign up, then click on *Personal* top right corner, then *View API keys*.

## Installing VoiceSim
* Download the zip of this repository and expand the zip to your install folder of choice on the PC running MSFS
* pip install keyboard pygame pyaudio requests Python-SimConnect 
* In the install folder, copy config_sample.py file to config.py
* Edit config.py to insert your OpenAI API key

## Using VoiceSim
Start MSFS in a window (not full screen). Open a command prompt window and change folder to VoiceSim install folder.
### If you are going to use VR
Start VR (MSFS CTRL + TAB), put on your headset, and wait for game to appear in the VR headset. Now take off your headset and use ALT + TAB to select the previously open command prompt window. Start VoiceSim by typing *python voice_sim.py*. Now put back your VR headset.
### If you are not using VR
Click on the previously opened command prompt. Start VoiceSim by typing *python voice_sim.py*. Now click on the MSFS window and make it full screen.

### Giving commands
Press and hold the trigger key, ALT, on the keyboard. Wait for a double beep sound. While continuing to hold the trigger key, speak your command. Release the trigger key. You will see your command converted to text, and the text converted to a SIMCONNECT command. If you are in the cockpit, you will see the control being set.

### Notes
* Rarely the OpenAI Whisper or GPT-3 API will time out, perhaps due to excessive load. Repeat the command if you do not see the change in the cockpit within 12 seconds
* If you are using speakers for sound, the microphone will pick up the aircraft engine noise along with your voice command. This can lower the accuracy of speech to text conversion. Use a directional microphone, bring the microphone closer to your mouth, or use a headset. This is not a problem when using VR because MSFS sounds will be produced in the VR headset
* Make sure the recording level for the microphone in Windows sound control panel is set to maximum
* Not all MSFS commands are available. Please see the prompt.py file for available commands. You can easily add more commands; see below.

## Advanced Configuration
* To change the default trigger key ALT, edit the config.py and change the 'trigger_key' setting. [Click here](https://github.com/boppreh/keyboard/blob/master/keyboard/_canonical_names.py) to see list of available key names that you can use. At this time, you cannot use modifiers; for example CTRL + P is not possible. All key names must be entered in lowercase. If you do not want to trigger from keyboard, set 'trigger_key' to ''. Make sure that the trigger key is not being used by MSFS
* If you are using a joystick, such as a yoke, you can use a button on the joystick as trigger. Follow these steps to configure the joystick with VoiceSim:
	1. To list available joysticks, run the list_joysticks.py program. Note down the ID of the joystick you want to use with VoiceSim
	2. To select the trigger button on the preferred joystick, run the list_joystick_buttons.py program with the ID of the joystick noted above. Then press the button on the joystick that you want to use as a trigger for VoiceSim. Note down the ID of the button
	3. Edit the config.py file to configure the joystick ID and button ID found in the above steps
	4. Make sure that MSFS is not using the same joystick button for anything
	5. If you do not want to trigger with a joystick button, set both 'joystick_id' and 'button' to None. Do not use any quotes around None
* By default, VoiceSim uses the Windows default recording device to get voice commands. If you have multiple microphones, you can configure which microphone should be used:
	1. Run the list_audio_devices.py program to get the ID of the *input device* you want to use
	2. Edit the config.py file to set the "audio_record_device_id" to the input device ID noted above. To have VoiceSim select windows default output device, set "audio_playback_device_id" to None
* By default, VoiceSim uses the Windows default playback device to provide audio notifications, such as acknowledge trigger button press. If you have multiple playback devices, you can configure which playback device should be used:
	1. Run the list_audio_device.py program to get the ID of the *output device* you want to use. Note that your VR headset must be started in order to detect the headset as an audio output device
	2. Edit the config.py file to set the "audio_playback_device_id" to the output device ID noted above. To have VoiceSim select windows default output device, set "audio_playback_device_id" to None
## Adding Voice Commands
You can add more commands to the prompt.py file. To see available commands please [see this SIMMCONECT source code file](https://github.com/odwdinc/Python-SimConnect/blob/master/SimConnect/EventList.py).
* OpenAI limits the total length of the prompt and response for the model being used by VoiceSim to 2,049 tokens. A token is roughly 4 characters excluding spaces. You can get an exact count of tokens in the prompt by pasting the prompt on [OpenAI Playground](https://platform.openai.com/playground)
* To workaround the prompt length limit, you can create prompt files per aircraft or scenario. In the near future, VoiceSim will allow very large prompts by uploading prompt files to OpenAI
* Sometimes Whisper speech-to-text misses the 's' sound, for example in "brakes". You must create prompt to cover brake and brakes
* Make sure to thoroughy test the prompt on [OpenAI Playground](https://platform.openai.com/playground) before using it. The settings on playground are as follows:
	* Mode: Complete
	* Model: text-babbage-001
	* Temperature: 0
	* Maximum length: 23
	* Stop sequences: [Press return key]
	* Top P: 1
	* Frequency penalty: 0
	* Presence penalty: 0
	* Best of: 1
	* Inject start text: [Leave blank]
	* Inject restart text: [Leave blank]
	* Show probabilities: Off
## Cost
VoiceSim uses two APIs from Open AI. The Whisper API is used for converting speech to text, and then the Completions API is used with GPT-3 model "text-babbage-001" to convert the text into a SIMCONNECT command. At the time of writing of this document, the costs of using these APIs is as follows:

* Whisper - $0.006 / minute (rounded to the nearest second)
* GPT-3 with Babbage - $0.0005 / 1K tokens

A token is roughly 4 characters excluding spaces. The tokens in an API call to completions API includes the tokens in the prompt (request message sent to the API), as well as the tokens in the response (the SIMMCONECT command).

You can [get current pricing here](https://openai.com/pricing).
## In the Works
I am currently working on adding the following features:
* Automatic MSFS start detect and start
* Tolerate sound device changes made by VR start
* More voice commands
* A log to allow troubleshooting after play is completed
* Audio notifications for command executed and failed
* Ability to set volume for audio notifications
## Contributing
Any contributions are much appreciated! Please open a pull request.
## Contact
If you find this project useful, or have any questions or suggestions, please do send an email to me at paruljain@hotmail.com. This will motivate me to continue building.