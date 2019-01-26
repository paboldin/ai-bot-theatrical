
import hashlib
import os
import re
import sys

from synthesize_file import synthesize_text_file, synthesize_ssml_file
from transcribe_streaming_mic import recognize_microphone_stream

LANG='ru-RU'
TTS_CLIENT = None

synthesizer = synthesize_text_file

SOUND_DIR='sound_dir'

def play(filename):
    os.system("mpg123 {}".format(filename))

def synthesize_and_play(txt):
    txt_hash = hashlib.md5(txt.encode('utf-8')).hexdigest()
    filename = os.path.join(SOUND_DIR, '{}.mp3'.format(txt_hash))
    if not os.path.isfile(filename):
        with open(filename, "wb") as fh:
            synthesizer(txt, TTS_CLIENT, fh, lang=LANG)
    play(filename)

class ScriptReader(object):
    def __init__(self, filename, callback, lang=LANG):
        self.filename = filename
        self.callback = callback
        self.lang = LANG

        self.update()

    @staticmethod
    def read_script(filename):
        script = {}

        with open(filename, encoding='utf-8') as fh:
            it = iter(fh)
            try:
                while True:
                    k = next(it).lower().strip()
                    v = next(it).lower().strip()
                    script[k] = v
            except StopIteration:
                pass

        return script

    def update(self):
        self.script = self.read_script(self.filename)

    def __call__(self, transcript, is_final=False):
        transcript = transcript.lower().strip()

        replica = self.script.get(transcript)

        if not replica and is_final:
            replica = self.script.get('default')

        if not replica:
            return

        print("Got {}, respond with {}".format(transcript, replica))

        self.callback(replica)

        return True

class StopIt(Exception):
    pass

class Listener(object):
    def __init__(self, reader):
        self.reader = reader

    def __call__(self, responses):
        for response in responses:
            if not response.results:
                continue

            # The `results` list is consecutive. For streaming, we only care about
            # the first result being considered, since once it's `is_final`, it
            # moves on to considering the next utterance.
            result = response.results[0]
            if not result.alternatives:
                continue

            #print(result, result.alternatives[0].transcript, "is_final = ", result.is_final)

            #if result.stability < 0.5:
                #if result.is_final:
                    #return
                #continue

            for alternative in result.alternatives:
                transcript = alternative.transcript

                print(transcript, result.is_final)

                if re.search(r'\b(сдохни блядь|сдохни сука)\b', transcript, re.I):
                    print('Exiting..')
                    raise StopIt()

                if re.search(r'\bсмени пластинку\b', transcript, re.I):
                    print('Updating..')
                    self.reader.update()
                    return

                if self.reader(transcript, result.is_final):
                    # Force it to reconnect
                    return

            if result.is_final:
                return


def main():
    global TTS_CLIENT
    from google.cloud import texttospeech
    TTS_CLIENT = texttospeech.TextToSpeechClient()

    try:
        filename = sys.argv[1]
    except IndexError:
        filename = 'script-%s.txt' % LANG

    script_reader = ScriptReader(
            filename,
            synthesize_and_play,
            lang=LANG)

    listener = Listener(script_reader)

    while True:
        try:
            recognize_microphone_stream(listener, lang=LANG, add_noise=100)
        except StopIt:
            break

if __name__ == '__main__':
    main()
