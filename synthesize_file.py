#!/usr/bin/env python

# Copyright 2018 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Text-To-Speech API sample application .

Example usage:
    python synthesize_file.py --text resources/hello.txt
    python synthesize_file.py --ssml resources/hello.ssml
"""

import argparse
import time


from google.cloud import texttospeech

LANG='en-US'

VOICE_NAME='ru-RU-WaveNet-A'

# [START tts_synthesize_text_file]
def synthesize_text_file(text, client, out, lang=LANG):
    """Synthesizes speech from the input file of text."""
    input_text = texttospeech.types.SynthesisInput(text=text)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.types.VoiceSelectionParams(
        language_code=lang,
        name=VOICE_NAME)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    t1 = time.time()
    response = client.synthesize_speech(input_text, voice, audio_config)

    # The response's audio_content is binary.
    out.write(response.audio_content)
    print(time.time() - t1)
# [END tts_synthesize_text_file]


# [START tts_synthesize_ssml_file]
def synthesize_ssml_file(ssml, client, out, lang=LANG):
    """Synthesizes speech from the input file of ssml.

    Note: ssml must be well-formed according to:
        https://www.w3.org/TR/speech-synthesis/
    """
    input_text = texttospeech.types.SynthesisInput(ssml=ssml)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.types.VoiceSelectionParams(
        language_code=lang,
        name=VOICE_NAME)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3)

    t1 = time.time()
    response = client.synthesize_speech(input_text, voice, audio_config)

    # The response's audio_content is binary.
    out.write(response.audio_content)
    print(time.time() - t1)
# [END tts_synthesize_ssml_file]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--text',
                       help='The text file from which to synthesize speech.')
    group.add_argument('--ssml',
                       help='The ssml file from which to synthesize speech.')

    args = parser.parse_args()

    if args.text:
        synthesize_text_file(args.text)
    else:
        synthesize_ssml_file(args.ssml)
