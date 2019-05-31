import re
import ast
import unicodedata

import operator as op
import itertools as it

import enchant
import langdetect

from stop_words import get_stop_words

from nltk.stem import WordNetLemmatizer
from nltk.stem.snowball import EnglishStemmer, FrenchStemmer
from nltk.corpus import stopwords

from french_lefff_lemmatizer.french_lefff_lemmatizer \
    import FrenchLefffLemmatizer

from utils import (
    scandir_r,
    get_path_elems_unix,
)


### basic

def clean(s):
    return s.strip().lower()


def tokenize(delim=' '):
    def _tokenize(text):
        return [t.strip() for t in text.split(delim)]
    return _tokenize


### io

def read_dictfile(path):
    with open(path) as io:
        yield from map(ast.literal_eval, io)


def get_words(path, ignore='@@', i=None, j=None):
    with open(path) as io:
        matches = filter(match(ignore, f=op.not_), io)
        yield from it.islice((w.strip() for w in matches), i, j)


def from_logs(*folders, root=None, filename='preds.txt'):
    for f in (it.chain.from_iterable(map(scandir_r, folders))
              if folders else scandir_r(root)):
        if f.name == filename:
            word = get_path_elems_unix(f.path, -2)
            with open(f.path) as io:
                preds = [p.strip() for p in io]
            yield word, preds


def sort_by_word(path):
    """
    return list of words and their lists of reverse image
    predictions sorted by the words in alphabetical order
    """
    return sorted(from_logs(path), key=lambda s: s[0].lower())


### web lang tools

GL = {'en': 'us'}


def lang_params(lang, as_list=False, throw=False):
    if lang is None:
        if throw:
            raise ValueError('lang is None')
        else:
            return ''
    gl = GL.get(lang, lang)
    params = ['hl=' + lang, 'lr=lang_' + lang,
              'gl=' + gl, 'cr=country' + gl.upper()]
    return params if as_list else '&'.join(params)


### stop words

stop_words_nltk_fr = set(stopwords.words('french'))
stop_words_nltk_en = set(stopwords.words('english'))

stop_words_alt_fr = set(get_stop_words('fr'))
stop_words_alt_en = set(get_stop_words('en'))


### POS

def get_pos(label_dict, src='en', t='fr'):
    try:
        return label_dict['pos_list'][0]
    except: pass
    try:
        return label_dict['pos_and_words'][0][0]
    except: pass
    try:
        return label_dict['pos_wp_in_' + src][0]
    except: pass
    try:
        return label_dict['pos_wp_out_' + t][0]
    except: pass


ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'
POS_CODE_DCT = frozenset({'adjective': ADJ, 'adverb': ADV,
                          'noun': NOUN, 'verb': VERB}.items())


def get_pos_code(labels, pos_code_dict=POS_CODE_DCT):
    if type(pos_code_dict) != dict:
        pos_code_dict = dict(pos_code_dict)
    def _get_pos_code(w):
        try:
            for entry in labels:
                if entry['w'] == w:
                    return pos_code_dict[get_pos(entry).lower()]
        except:
            pass
    return _get_pos_code


### stemming

STEMMERS = {'en': EnglishStemmer().stem,
            'fr': FrenchStemmer().stem}

def stem_compare(w1, w2, lang='en'):
    stemmer = STEMMERS[lang]
    return stemmer(w1) == stemmer(w2)


### lemmatizing

LEMMATIZERS = {'en': WordNetLemmatizer,
               'fr': FrenchLefffLemmatizer}


def get_lem(lemmer_class, get_pos_code, **kwargs):
    """
    e.g. lemmer_class = FrenchLefffLemmatizer
    kwargs = dict(with_additional_file=False, load_only_pos=['n', 'a'])
    lemmer = get_lem(lemmer_class, get_pos_code(labels), **kwargs)
    """
    lemmer = lemmer_class(**kwargs)
    def _get_lem(w):
        pos_code = get_pos_code(w)
        # if pos_code is None, lemmatizes as noun (guess)
        if pos_code is not None:
            return lemmer.lemmatize(w, pos_code)
    return _get_lem


### word dict lookup

def is_lang(lang):
    code = 'fr_FR' if lang.lower().startswith('fr') \
      else 'en_US' if lang.lower().startswith('en') \
      else (lang or 'en_US')
    dictionary = enchant.Dict(code)
    def _is_lang(word):
        ld_check  = lang in {lr.lang for lr in langdetect.detect_langs(word)}
        dct_check = dictionary.check(word)
        return ld_check or dct_check
    return _is_lang


### filtering / matching

LIST = ('Ll', 'Lu', 'Lo', 'Lm', 'Lt')


def has_letter(s):
    return next(c in LIST for c in map(unicodedata.category, s))


def is_one_word(s):
    return ' ' not in s


def match(fixed=None, regex=None,
          f=lambda x:x, compile_re=True):
    if fixed:
        return lambda s: f(fixed in s)
    elif regex:
        if compile_re:
            regex = re.compile(regex)
        return lambda s: f(re.search(regex, s))
    return lambda s: True


### ngrams

def ngrams(doc, n, delim=None, nospace=True):
    if delim and isinstance(doc, (str, bytes)):
        doc = doc.split(delim)
    for i in range(len(doc)-n+1):
        if nospace and re.search('\s', doc[i:i+n]):
            continue
        yield doc[i:i+n]