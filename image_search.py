import os
import uuid

import traceback as tb

import ujson as json

from PIL import Image
from bs4 import BeautifulSoup

from web import request
from utils import is_, get_logger
from nlp_utils import lang_params


LOGGER = get_logger(__name__)


def QUERY_URL(query):
    return 'https://www.google.com/search?tbm=isch&q=' + query


def get_imgs_from_soup(soup):
    img_elems = soup.find_all('div', {'class': 'rg_meta'})
    metadata  = (json.loads(e.text) for e in img_elems)
    return [(d['ou'], d['ity']) for d in metadata]


def get_imgs(query, lang=None, debug=None):
    query_url = QUERY_URL(query)
    if is_(lang):
        query_url += '&' + lang_params(lang)
    if debug:
        print('query_url for %s: %s' % (query, query_url))
    resp  = request(query_url, sleep=(.5, 1.5))
    soup  = BeautifulSoup(resp.text, 'lxml')
    return get_imgs_from_soup(soup)


def save_img(url, img_type, save_dir, rm_meta=False):
    raw_img   = request(url, sleep=(.5, 1.5)).content
    ext       = img_type or 'jpg'
    name      = str(uuid.uuid4().hex) + '.' + ext
    save_path = os.path.join(save_dir, name)
    with open(save_path, 'wb+') as f:
        f.write(raw_img)
    if rm_meta:
        Image.open(save_path).save(save_path)


def save_imgs(imgs, save_dir, n_img=float('inf')):
    for i, (url, img_type) in enumerate(imgs):
        if i >= n_img:
            break
        try:
            save_img(url, img_type, save_dir)
        except:
            LOGGER.error(tb.format_exc())


def image_search(query, lang=None, save=None, debug=None):
    LOGGER.info('START (Phase 1) Getting Image URLs for: %s' % query)
    query = query.strip().replace(' ', '+')
    images = get_imgs(query, lang, debug)
    if save:
        save_imgs(images, save)
    urls, _ = zip(*images)
    paths_str = '\n' + ''.join('%s: %s\n' % (i+1, path)
                               for i, path in enumerate(urls))
    LOGGER.info('DONE (Phase 1) Getting Image URLs for: %s\n- URLs -%s'
                % (query, paths_str))
    return urls