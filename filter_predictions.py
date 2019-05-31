import random

import traceback as tb
import itertools as it

from collections import Counter, defaultdict

import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from fuzzywuzzy.fuzz import partial_ratio

from nlp_utils import (
    clean,
    ngrams,
    is_lang,
    get_pos,
    tokenize,
    has_letter,
    is_one_word,
    STEMMERS,
)
from utils import (
    dump,
    load,
    dedupe,
    get_logger,
)


LOGGER = get_logger(__name__)


### filtering

def top_counts(iterable):
    counts = Counter(iterable)
    hi     = counts.most_common(1)[0][1]
    tops   = it.takewhile(lambda vc: vc[1] >= hi, counts.most_common())
    return list(tops)


def filter_preds(preds, query=None, lang=None,
                 phrase_type=None, final=None):
    preds = list(map(clean, preds))

    if query:
        clean_q = clean(query)
        preds   = [p for p in preds if p != clean_q]

    preds_filtr = (
        filter(is_one_word, preds)
            if phrase_type == 'word'
        else it.chain.from_iterable(
            filter(has_letter, map(clean, p.split())) for p in preds)
            if 'fragment' in phrase_type
        else preds
    )

    if lang:
        preds_filtr = filter(is_lang(lang,), preds_filtr)

    try:
        if preds_filtr:
            tops = top_counts(preds_filtr)
            if final:
                final_pred = tops[0][0] if final == 'first' \
                        else random.choice(tops)[0]
                if phrase_type == 'fragment-orig':
                    return next(s for s in preds if final_pred in s)
                return final_pred
            return tops
    except:
        LOGGER.error(tb.format_exc())


def oracle(word_preds, labels, pos_counts, src='en', t='fr'):
    n_words, score = len(word_preds), 0
    pos_scores = defaultdict(float)
    corrects = {}
    for (word, preds), label_dict in zip(word_preds, labels):
        final_preds_and_words = set(map(clean, preds)) | set(
            word for p in preds for word in map(clean, p.split()))
        if label_dict['t'] in final_preds_and_words:
            corrects[word]= label_dict['t'], get_pos(label_dict, src, t)
            score += 1.
            pos_scores[get_pos(label_dict, src, t)] += 1.
    return score / n_words, {pos: pos_scores[pos] / pos_counts[pos]
                             for pos in pos_counts}, corrects


def scorer(preds, labels, pos_counts, src='en', t='fr', verbose=0, oracle=None):
    n_words, score = len(preds), 0
    pos_scores = defaultdict(float)
    for pred, label_dict in zip(preds, labels):
        if pred == label_dict['t']:
            score += 1.
            pos_scores[get_pos(label_dict, src, t)] += 1.
        elif verbose:
            if oracle and label_dict['w'] not in oracle:
                continue
            print(label_dict['w'], '- t:', label_dict['t'], '| p:', pred)
    return score / n_words, {pos: pos_scores[pos] / pos_counts[pos]
                             for pos in pos_counts}


def tfidf_word_feats(word_matrix, ngrams=(2,)):
    docs_by_word = [' '.join(pred_list) for pred_list in word_matrix]

    # by individual word
    tfidf_word_results = []
    tfidf_wrd = TfidfVectorizer(tokenizer=tokenize())
    word_scores = tfidf_wrd.fit_transform(docs_by_word).toarray()
    word_feat_names = tfidf_wrd.get_feature_names()
    for i, row in enumerate(word_scores):
        tfidf_word_results.append({pred_name: score
             for score, pred_name in zip(row, word_feat_names)
             if score > 0})

    # by n-gram, for multiple n
    tfidf_ng_results = []

    # FIXME need to merge dicts over all n
    for n in ngrams:
        tfidf_char = TfidfVectorizer(analyzer='char', ngram_range=(n, n))
        char_scores = tfidf_char.fit_transform(docs_by_word).toarray()
        char_feat_names = tfidf_char.get_feature_names()
        for i, row in enumerate(char_scores):
            tfidf_ng_results.append({ng: score
                for score, ng in zip(row, char_feat_names)
                if score > 0 and ' ' not in ng})

    return list(zip(tfidf_word_results, tfidf_ng_results))


def preds_to_words(preds, stop_words=(), rank=False, minlen=2):
    for i, p in enumerate(preds):
        for word in filter(has_letter, p.split()):
            if word not in stop_words and len(word) >= minlen:
                yield (word, i+1) if rank else word


def normalize_dict(d):
    m, M = min(d.values()), max(d.values())
    normalizer = (lambda v: 1./len(d)) if M == m \
            else (lambda v: (v-m)/(M-m))
    return {k: normalizer(d[k]) for k in d}


def word_row_feats(word, words_w_ranks, lang, ngram_lens=(2,),
                   tfidf_words=None, tfidf_ngrams=None):
    if not tfidf_words:  tfidf_words  = defaultdict(lambda:1)
    if not tfidf_ngrams: tfidf_ngrams = defaultdict(lambda:1)

    # rank = harmonic sum of positions in pred list
    rank_scores = defaultdict(float)
    for w, rank in words_w_ranks:
        rank_scores[w] += 1./rank

    words, _ = zip(*words_w_ranks)
    deduped  = list(dedupe(words))

    # unnormalized word counts
    counts = Counter(words)

    # stem counts
    stemmer = STEMMERS[lang]
    stems = {w: stemmer(w) for w in deduped}
    stem_counter = Counter(stems[w] for w in words)
    stem_counts = {w: stem_counter[stems[w]] for w in deduped}

    # ngrams
    ngram_counts = defaultdict(float)
    for n in ngram_lens:
        word_ngrams = {word: list(ngrams(word, n)) for word in deduped}
        ngram_counter = Counter(ng for w in words for ng in word_ngrams[w])
        for w in deduped:
            # max?
            ngram_counts[n, w] = np.mean([ngram_counter[ng] * tfidf_ngrams[ng]
                                          for ng in word_ngrams[w]])

    # fuzziness
    seen = set()
    fuzzy_score = {}
    for i in range(len(words)):
        wi = words[i]
        if wi not in seen:
            seen.add(wi)
            fuzzy_score[wi] = np.mean([partial_ratio(wi, words[j])
                                      for j in range(len(words)) if j != i])

    # substrings
    seen = set()
    substring_score = {}
    for i in range(len(words)):
        wi = words[i]
        if wi not in seen:
            seen.add(wi)
            substring_score[wi] = np.mean([
                wi in words[j] for j in range(len(words)) if j != i])

    score_dicts = list(map(normalize_dict,
        [ngram_counts[n] for n in ngram_lens] +
        [counts, stem_counts, fuzzy_score, substring_score, rank_scores]
    ))

    scores = {w: list(dct[w] * tfidf_words[w]
                      for dct in score_dicts) for w in deduped}

    # weighted mean? or keep as tuple? or use as feat vectors?
    s, W = max([(np.mean(v),w) for w,v in scores.items()])
    return W


def predict(word_preds, stop_words=(), k=None,
            t='fr', query=False, lang=False,
            save_pred=None, load_pred=None):

    if load_pred:
        word_preds = load(load_pred)

    else:
        word_preds = list(map(list, word_preds))

        for i in range(len(word_preds)):
            preds = list(
                filter(has_letter,
                       map(clean, word_preds[i][1][:k])))

            if stop_words:
                preds = [w for w in preds if w not in stop_words]

            if query: # filter src word
                clean_q = clean(word_preds[i][0])
                preds = [p for p in preds if p != clean_q]

            if lang: # filter by target language
                preds = list(filter(is_lang(t), preds))

            word_preds[i][1] = preds

    if save_pred:
        dump(word_preds, save_pred)


    pred_words_matrix = [list(preds_to_words(wrd_pred, stop_words))
                         for _, wrd_pred in word_preds]
    # src-word i -> (tfidf-word scores, tf-idf ngram scores)
    tfidf_results = tfidf_word_feats(pred_words_matrix)

    for (wrd, wrd_pred), (tfidf_words, tfidf_ngs) in \
            zip(word_preds, tfidf_results):
        words_w_ranks = list(preds_to_words(wrd_pred, stop_words, rank=True))
        yield word_row_feats(wrd, words_w_ranks, t,
                             tfidf_words=tfidf_words,
                             tfidf_ngrams=tfidf_ngs,
                             )


