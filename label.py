import re

import traceback as tb

from googletrans import Translator
from wiktionaryparser import WiktionaryParser

from utils import is_
from nlp_utils import get_words


### google translate + POS

def from_trans_dict(dct):
    pos_and_words = []
    try:
        for entry in dct:
            # words ranked in order of relevance
            pos_and_words.append((entry[0], entry[1]))
    except:
        pass
    return pos_and_words or None


def from_def_dict(dct):
    pos_list = []
    try:
        for entry in dct:
            pos_list.append(entry[0])
    except:
        pass
    return pos_list or None


def get_pos(X):
    ed = X.extra_data
    pos_list = from_def_dict(ed['definitions'])
    pos_and_words = from_trans_dict(ed['all-translations'])
    return pos_list, pos_and_words


def gtrans(w, dest, src=None, translator=None, **trans_kwargs):
    if translator is None:
        translator = Translator(**trans_kwargs)
    trans = translator.translate(w, src=src, dest=dest)
    pos_list, pos_and_words = get_pos(trans)
    return {'w': w, 'src': src, 'dest': dest,
            't': trans.text, 'pos_list': pos_list,
            'pos_and_words': pos_and_words}


### wiktionary morph + pos

def noun_gender(text):
    try:
        gpat    = re.compile('(?<=\xa0)((m|f|m-p|f-p|mf|m\|g2=f),* *)*')
        genders = re.search(gpat, text)
        return list(filter(None, re.split(',| +', genders.group())))
    except:
        pass


FORM_OF_DEFN = 'masculine', 'feminine', 'plural', 'singular'


def wp_morph(txt, pos):
    morph = []
    if len(txt) == 2 and ' of ' in txt[1] \
            and any(i in txt[1] for i in FORM_OF_DEFN):
        of_form = txt[1].split(' of ')[0]
        morph.append(of_form)
    if len(txt) > 0 and 'noun' in pos.lower():
        genders = noun_gender(txt[0])
        if genders:
            morph.append(genders)
    return morph or None


def get_info(w, lang=None, parser=None,
             debug=False, postfix=None):
    try:
        if parser is None:
            parser = WiktionaryParser()
        info = parser.fetch(w, lang)[0]['definitions']
        pos_list, morph_list = [], []
        for info_dct in info:
            pos = info_dct['partOfSpeech']
            txt = info_dct['text']
            pos_list.append(pos)
            morph_list.append(wp_morph(txt, pos))
        result_dict = {'w': w, 'src': lang[:2],
                       'pos_wp': pos_list,
                       'morph': morph_list}
        return {k + postfix: v for k, v in result_dict.items()} \
            if is_(postfix) else result_dict
    except:
        if debug:
            tb.print_exc()
        return {}


### general

def merge_dicts(*dicts):
    result = {}
    for dct in dicts:
        for k in dct:
            if k in result and result[k] != dct[k]:
                result[k] = [result[k], dct[k]]
            else:
                result[k] = dct[k]
    return result


if __name__ == '__main__':
    URLS = None
    T = Translator(URLS)
    WP = WiktionaryParser()

    inputs     = ('train/english_clean', 'train/french_clean')
    outputs    = ('labels/en_labels2.txt', 'labels/fr_labels2.txt')
    lang_pairs = (('english', 'french'), ('french', 'english'))

    for inpath, outpath, (inlang, outlang) in zip(inputs, outputs, lang_pairs):
        with open(outpath, 'w') as io:
            for w in get_words(inpath):
                try:
                    gdict  = gtrans(w, src=inlang[:2],
                                    dest=outlang[:2],
                                    translator=T)
                    wdict  = get_info(w, lang=inlang, parser=WP,
                                      postfix='_in_'+inlang[:2])
                    wdict2 = get_info(w, lang=outlang, parser=WP,
                                      postfix='_out_'+outlang[:2])
                    D = merge_dicts(gdict, wdict, wdict2)
                    print(D, file=io)
                    print(D)
                except:
                    print('ERR: %s\n%s' % (w, tb.format_exc()))
        print('\n~~~\n')