
import os

from synthesize_file import synthesize_text_file, synthesize_ssml_file
from transcribe_streaming_mic import recognize_microphone_stream

LANG='ru-RU'
TTS_CLIENT = None

synthesizer = synthesize_text_file

SOUND_DIR='sound_dir'

def play(filename):
    os.system("mpg123 {}".format(filename))

def synthesize_and_play(txt):
    txt_hash = hash(txt)
    filename = os.path.join(SOUND_DIR, '{}.mp3'.format(txt_hash))
    if not os.path.isfile(filename):
        with open(filename, "wb") as fh:
            synthesizer(txt, fh, TTS_CLIENT, lang=LANG)
    play(filename)

class ScriptReader(object):
    def __init__(self, filename, callback, lang=LANG):
        self.script = self.read_script(filename)
        self.callback = callback
        self.lang = LANG

    @staticmethod
    def read_script(cls, filename):
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

    def __call__(self, transcript):
        transcript = transcript.lower().strip()

        replica = self.script.get(transcript, transcript.get('default'))

        print("Got {}, respond with {}".format(transcript, replica))

        if not replica:
            return

        self.callback(replica)

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

            # Display the transcription of the top alternative.
            transcript = result.alternatives[0].transcript

            # Display interim results, but with a carriage return at the end of the
            # line, so subsequent lines will overwrite them.
            #
            # If the previous result was longer than this one, we need to print
            # some extra spaces to overwrite the previous result

            if result.is_final:
                # Exit recognition if any of the transcribed phrases could be
                # one of our keywords.
                if re.search(r'\b(сдохни блядь|сдохни сука)\b', transcript, re.I):
                    print('Exiting..')
                    break

                self.reader(transcript)

def main():
    global TTS_CLIENT
    from google.cloud import texttospeech
    TTS_CLIENT = texttospeech.TextToSpeechClient()

    script_reader = ScriptReader(
            'script-%s.txt' % LANG,
            synthesize_and_play,
            lang=LANG)

    listener = Listener(script_reader)

    recognize_microphone_stream(listener, lang=LANG)

if __name__ == '__main__':
    main()
