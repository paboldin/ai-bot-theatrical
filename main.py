
import collections
import hashlib
import os
import re
import sys
import pprint

import numpy

from nltk.corpus import stopwords
from gensim.models import KeyedVectors
import pymorphy2

from synthesize_file import synthesize_text_file, synthesize_ssml_file
from transcribe_streaming_mic import recognize_microphone_stream

LANG='ru-RU'
TTS_CLIENT = None

synthesizer = synthesize_text_file

SOUND_DIR='sound_dir'

if os.name == 'nt':
    import playsound
    def play(filename):
        playsound.playsound(filename)
else:
    def play(filename):
        os.system("mpg123 {}".format(filename))

SSML = """
<?xml version="1.0"?>
<speak version="1.1" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://www.w3.org/2001/10/synthesis
                 http://www.w3.org/TR/speech-synthesis11/synthesis.xsd"
       xml:lang="{lang}">
    {TXT}
</speak>
"""
SSML = SSML.format(lang=LANG, TXT="{TXT}")

def synthesize_and_play(txt):
    txt_hash = hashlib.md5(txt.encode('utf-8')).hexdigest()
    filename = os.path.join(SOUND_DIR, '{}.mp3'.format(txt_hash))
    synthesizer = synthesize_text_file
    if txt[0] == '<':
        synthesizer = synthesize_ssml_file
        txt = SSML.format(TXT=txt)
        print(txt)
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

    @classmethod
    def _text_process(cls, txt, is_input=False):
        txt = txt.lower().strip()
        txt = re.sub("^\* *", "", txt)
        if not is_input:
            return txt
        txt = re.sub("ё", "е", txt)
        return re.sub("[.,;:?!]", "", txt)

    @classmethod
    def read_script(cls, filename):
        script = collections.OrderedDict()

        with open(filename, encoding='utf-8') as fh:
            it = iter(fh)
            try:
                while True:
                    k = cls._text_process(next(it), is_input=True)
                    if not k:
                        continue
                    v = cls._text_process(next(it))
                    if not v:
                        continue
                    script[k] = v
            except StopIteration:
                pass

        return script

    def update(self):
        self.script = self.read_script(self.filename)

    def add(self, key, value):
        key = self._text_process(key, is_input=True)
        value = self._text_process(value)

        self.script[key] = value

    def remove(self, key):
        key = self._text_process(key, is_input=True)
        if key in self.script:
            del self.script[key]

    def __call__(self, transcript, is_final=False):
        transcript = self._text_process(transcript, is_input=True)

        replica = self.script.get(transcript)

        if not replica and is_final:
            replica = self.script.get('ничего непонятно')

        if not replica:
            return

        print("Got {}, respond with {}".format(transcript, replica))

        self.callback(replica)

        return True

class W2VScriptReader(ScriptReader):
    stopwords = stopwords.words('russian')
    pymorphy = pymorphy2.MorphAnalyzer()

    grammar_map_POS_TAGS = {
        'NOUN': '_NOUN',
        'VERB': '_VERB', 'INFN': '_VERB', 'GRND': '_VERB', 'PRTF': '_VERB', 'PRTS': '_VERB',
        'ADJF': '_ADJ', 'ADJS': '_ADJ',
        'ADVB': '_ADV',
        'PRED': '_ADP',
    }

    def __init__(self, *args, **kwargs):
        print("Loading word2vec...")
        self.w2v = KeyedVectors.load_word2vec_format('model/model.bin',
                binary=True, encoding='utf-8')
        print("done")

        super(W2VScriptReader, self).__init__(*args, **kwargs)

    @classmethod
    def _text_process(cls, txt, is_input=False, filter_stopwords=False):
        txt = txt.lower().strip()
        txt = re.sub("^\* *", "", txt)
        if not is_input:
            return txt
        txt = re.sub("ё", "е", txt)
        txt = re.sub("[.,;:?!]", "", txt)
        if filter_stopwords:
            txt = " ".join(x for x in txt.split() if x not in cls.stopwords)
        return txt

    def update_vecs(self):
        self.vectors = collections.OrderedDict()
        for key, value in self.script.items():
            self.add_vector_item(key, value)

    def to_vector(self, txt):
        total = numpy.zeros((self.w2v.vector_size,))
        txt = self._text_process(txt, is_input=True, filter_stopwords=True)

        words = txt.split()
        nwords = 0
        for word in words:
            parse = self.pymorphy.parse(word)[0]
            POS = parse.tag.POS
            if POS is None:
                print("dont know word", word)
                continue
            print(word, parse, POS)
            POS = self.grammar_map_POS_TAGS.get(POS)
            if POS is None:
                print("can't map word", word)
                continue
            word = parse.normal_form
            try:
                vec = self.w2v[word + POS]
                total += vec
                nwords += 1
            except KeyError:
                print("no word ", word + POS)
        return total / numpy.sqrt(numpy.dot(total, total) + 0.0001)

    def add_vector_item(self, key, value):
        if key == 'default':
            return
        vec = self.to_vector(key)
        self.vectors[key] = (vec, key, value)

    def lookup(self, key):
        lookup = self.to_vector(key)
        mindistance, element = float('+inf'), None
        for i, (vec, q, a) in enumerate(self.vectors.values()):
            d = lookup - vec
            distance = numpy.sqrt(numpy.dot(d, d))
            print(distance, q)
            if distance < mindistance:
                mindistance = distance
                element = (vec, q, a)
        print(mindistance, element[1], element[2])
        return element

    def update(self):
        super(W2VScriptReader, self).update()
        self.update_vecs()

    def add(self, key, value):
        key = self._text_process(key, is_input=True)
        value = self._text_process(value)

        self.script[key] = value
        self.add_vector_item(key, value)

    def remove(self, key):
        key = self._text_process(key, is_input=True)
        self.script.pop(key)
        self.vectors.pop(key)

    def __call__(self, transcript, is_final=False):
        exact = self._text_process(transcript, is_input=True)

        replica = self.script.get(exact)
        if not replica and not is_final:
            return

        if is_final:
            clear = self._text_process(transcript, is_input=True,
                    filter_stopwords=True)
            replica = self.lookup(clear)
            if replica:
                replica = replica[2]

        if not replica:
            replica = self.script.get('default')

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

                if not re.search(r'василиса', transcript, re.I):
                    if self.reader(transcript, result.is_final):
                        # Force it to reconnect
                        return
                    continue

                if re.search(r'\bумри\b', transcript, re.I):
                    print('Exiting..')
                    raise StopIt()

                if re.search(r'\bсмени пластинку\b', transcript, re.I):
                    print('Updating..')
                    self.reader.update()
                    return

                if re.search(r'\bпокажи сценарий\b', transcript, re.I):
                    pprint.pprint(self.reader.script)
                    return

                match = re.search( r'\bдобавить(?P<phrase>.*)ответить(?P<response>.*)\b', transcript, re.I)
                if result.is_final and match:
                    self.reader.add(match['phrase'], match['response'])
                    return

                match = re.search(r'\bубрать команду(?P<phrase>.*)\b',
                        transcript, re.I)
                if result.is_final and match:
                    self.reader.remove(match['phrase'])
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

    script_reader = W2VScriptReader(
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
