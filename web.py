import time
import random

import traceback as tb

import requests

from utils import is_, get_logger


LOGGER = get_logger(__name__)


### ua

DEFAULT_UA = ''

UA_HEADER = {'User-Agent': DEFAULT_UA}

UA_GEN = None


def get_ua(default=True, as_dict=True, ua_method='random'):
    global UA_GEN
    if default:
        return UA_HEADER if as_dict else DEFAULT_UA
    if UA_GEN is None:
        from fake_useragent import UserAgent
        UA_GEN = UserAgent()
    ua = getattr(UA_GEN, ua_method, DEFAULT_UA)
    return {'User-Agent': ua} if as_dict else ua


### proxy

PROXIES = []

RANDOMIZE = True
if RANDOMIZE:
    random.shuffle(PROXIES)


PROXY_TYPE = 'http'
if PROXY_TYPE == 'http':
    HTTP_PREFIX = HTTPS_PREFIX = 'http'
    HTTP_PORT = HTTPS_PORT = '3128'
else: # socks5
    HTTP_PREFIX = HTTPS_PREFIX = 'socks5'
    HTTP_PORT = HTTPS_PORT = '1080'

PROXY_USER = ''
PROXY_PASS = ''
if PROXY_USER and PROXY_PASS:
    PROXY_USER_PASS = '%s:%s@' % (PROXY_USER, PROXY_PASS)
else:
    PROXY_USER_PASS = ''

PROXY_HTTP_URL = '%s://%s{ip}:%s/' % (HTTP_PREFIX, PROXY_USER_PASS, HTTP_PORT)
PROXY_HTTPS_URL = '%s://%s{ip}:%s/' % (HTTPS_PREFIX, PROXY_USER_PASS, HTTPS_PORT)

CURRENT_PROXY = 0


def current_proxy(rotate=True):
    if not PROXIES:
        return 'NO PROXY'

    global CURRENT_PROXY
    curr_proxy = PROXIES[CURRENT_PROXY]
    if rotate:
        CURRENT_PROXY = (CURRENT_PROXY + 1) % len(PROXIES)
    return curr_proxy


def prev_proxy():
    if not PROXIES:
        return 'NO PROXY'
    return PROXIES[(CURRENT_PROXY - 1) % len(PROXIES)]


def get_proxy(p=None, rotate=True):
    if not PROXIES:
        return

    if is_(p):
        proxy_addr = p
    elif rotate:
        proxy_addr = current_proxy()
    else:
        proxy_addr = random.choice(PROXIES)

    return {'http': PROXY_HTTP_URL.format(ip=proxy_addr),
            'https': PROXY_HTTPS_URL.format(ip=proxy_addr)}


### requests

def slp(o):
    # o is either a number or an interval
    a, b = o if isinstance(o, (tuple, list)) else (o, None)
    if a and b:
        time.sleep(random.uniform(a, b))
    else:
        time.sleep(a)


def request(url, kind='get', sleep=None, **kw):
    resp = getattr(requests, kind)(url,
                                   headers=get_ua(),
                                   proxies=get_proxy(),
                                   **kw)
    if is_(sleep):
        slp(sleep)
    return resp


class BadStatusCode(Exception):
    def __init__(self, code='?'):
        self.code = code
        super().__init__('<%s>' % code)


def log_web_err(url, proxy=None, err_str=None, prefix='',
                kind='error', extra_err_msg=None):
    err_msg = prefix + '\nURL: %s\nProxy: %s\nErr:%s %s' \
              % (url, proxy or prev_proxy(), extra_err_msg,
                 err_str or tb.format_exc())
    getattr(LOGGER, kind)(err_msg)


def retry(url, requestor=None, n_tries=2, sleep=None,
          good_codes=(200,), reraise=True, always_sleep=True):
    do_request = (lambda: requestor(url)) if is_(requestor) \
            else (lambda: request(url))
    for i in range(n_tries):
        try:
            r = do_request()
            if always_sleep and is_(sleep):
                slp(sleep)
            if r.status_code in good_codes:
                return r
            raise BadStatusCode(r.status_code)
        except:
            if i >= n_tries - 1:
                if reraise: raise
                else: return
            prefix = '\nBAD REQUEST, RETRY (%s/%s)' % (i+2, n_tries)
            log_web_err(url, kind='warning', prefix=prefix)
            if not always_sleep and is_(sleep):
                slp(sleep)