from collections import defaultdict
from urllib import parse as urlparse

from bs4 import BeautifulSoup

from nlp_utils import lang_params
from utils import get_logger, sample
from selenium_methods import reverse_search_selenium
from web import (
    retry,
    prev_proxy,
    log_web_err,
    BadStatusCode,
    PROXIES,
)


LOGGER = get_logger(__name__)


def parse_reverse_prediction(resp, from_request=True):
    if from_request:
        resp = resp.text
    soup = BeautifulSoup(resp, 'lxml')
    card = soup.find('div', {'class': 'card-section'})
    # error if card is None or no such tag
    return card.next.nextSibling.a.text


class TriggeredCaptcha(Exception):
    pass


# 503/captcha fail tolerance
N_FAILS = 3

# if using proxies
CAPTCHA_COUNT = defaultdict(int)
N_PROXY_THRESH = 1

# if no proxies
_503_COUNT = 0


def check_ip():
    global _503_COUNT
    _503_COUNT += 1
    if _503_COUNT >= N_FAILS:
        LOGGER.fatal('EXIT Hit 503 threshold (%s), exiting' % N_FAILS)
        exit(1)
    else:
        LOGGER.error('Hit 503 Codes for %s image(s)' % _503_COUNT)


def check_proxies():
    if not PROXIES:
        return check_ip()
    proxy = prev_proxy()
    CAPTCHA_COUNT[proxy] += 1
    if CAPTCHA_COUNT[proxy] >= N_FAILS:
        LOGGER.error('PROXY %s hit 503 Codes for %s images, removing.'
                     ' %s proxies left.' % (proxy, N_FAILS, len(PROXIES)-1))
        PROXIES.remove(proxy)
    if len(PROXIES) < N_PROXY_THRESH:
        LOGGER.fatal('EXIT All proxies hit 503 threshold (%s), exiting' % N_FAILS)
        exit(1)


def check_captcha(ex, url, exit_on_many_503s=False, manual_solve=True):
    ret = None
    if isinstance(ex, BadStatusCode) and ex.code == 503:
        if exit_on_many_503s:
            check_proxies()
        elif manual_solve:
            ip = None if not PROXIES else prev_proxy()
            # TODO FIXME
            ret = reverse_search_selenium(ip, url)
        return ' (Captcha?)', ret
    return '', ret


def REVERSE_QUERY_URL(url, lang=None, shuffle_params=True, encode=True):
    if encode and '?' in url:
        url = urlparse.quote(url).replace('%25', '%')
    params = ['image_url=' + url]
    l_params = lang_params(lang, as_list=True)
    if l_params:
        params = l_params + params
    if shuffle_params and len(params) > 1:
        params = sample(params)
    return 'https://www.google.com/searchbyimage?' + '&'.join(params)


def bare_bones(url, lang=None, msg='', shuffle_params=True):
    query_url = REVERSE_QUERY_URL(url, lang, shuffle_params)
    LOGGER.info('START RETRY Reverse%s - %s' % (msg, query_url))
    is_web_err = True
    try:
        resp = retry(query_url, sleep=(2., 3.), n_tries=1)
        is_web_err = False
        pred = parse_reverse_prediction(resp)
        LOGGER.info('DONE RETRY Reverse%s [%s] - %s\n\t- Success on Proxy: %s'
                    % (msg, pred, query_url, prev_proxy()))
        return pred
    except Exception as ex:
        prefix = '\nFAIL: FINAL RETRY' if is_web_err else ''
        captcha_msg, ret = check_captcha(ex, query_url, False, False)
        if ret: return ret
        log_web_err(query_url, prefix=prefix, extra_err_msg=captcha_msg)


def reverse_search_url(url, lang=None, msg='',
                       shuffle_params=True,
                       n_tries=2, debug=None):
    query_url = REVERSE_QUERY_URL(url, lang, shuffle_params)
    if debug:
        print('Reversing %s: %s' % (msg, query_url))
    LOGGER.info('START Reverse%s - %s' % (msg, query_url))
    is_web_err = True
    try:
        resp = retry(query_url, sleep=(2., 3.), n_tries=n_tries)
        is_web_err = False
        pred = parse_reverse_prediction(resp)
        LOGGER.info('DONE Reverse%s [%s] - %s\n\t- Success on Proxy: %s'
                    % (msg, pred, query_url, prev_proxy()))
        return pred
    except Exception as ex:
        prefix = '\nFAIL: USED ALL RETRIES' if is_web_err else ''
        captcha_msg, ret = check_captcha(ex, query_url)
        if ret: return ret
        log_web_err(query_url, prefix=prefix, extra_err_msg=captcha_msg)
        if captcha_msg:
            return bare_bones(url, lang, msg)


def reverse_search_urls(query, *urls, lang=None, n_img=20, debug=None):
    LOGGER.info('START (Phase 2) Reverse Search for: %s\n' % query)
    preds = []
    for i, url in enumerate(urls):
        if len(preds) >= n_img:
            break
        pred = reverse_search_url(url, lang, msg=' #%s' % i, debug=debug)
        if pred and pred.strip():
            preds.append(pred)
    LOGGER.info('\nDONE (Phase 2) Reverse Search for: %s\n' % query)
    return preds
