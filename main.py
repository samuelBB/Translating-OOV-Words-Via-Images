import os.path as osp

from utils import (
    is_,
    arg,
    parse_args,
    mkdir_p,
    time_stamp,
    init_logging,
    get_logger,
    write_lines,
    read_lines,
)


# TODO only do parts of pipeline
opts = parse_args(
    arg('-name', default='fr-clean'),

    arg('-f', '--file',   default='train/french_clean'),
    # if you want 18th word do 17
    arg('-i', '--start',  type=int, default=76),
    arg('-j', '--stop',   type=int),

    arg('-q', '--query',  nargs='*'),

    arg('-s', '--src',    default='fr'),
    arg('-t', '--target', default='en'),

    arg('-n', '--n-img',  type=int, default=20),

    # pipeline
    arg('-is', '--sch',   action='store_true'),
    arg('-rs', '--rsch',  action='store_true'),
    arg('-pred',          action='store_true'),

    # use saved
    arg('-load-urls'),
    arg('-load-preds'),
)

name = opts.name + '__' if is_(opts.name) else ''
RESULT_PREFIX = osp.join('reverse-img-final-preds',
                         '%s_to_%s' % (opts.src, opts.target),
                         name + time_stamp())
mkdir_p(RESULT_PREFIX)

fh = init_logging(file=osp.join(RESULT_PREFIX, 'log.log'),
                  stdout=True)
LOGGER = get_logger(__name__, main=True)


from nlp_utils import get_words
from image_search import image_search
from reverse_image_search import reverse_search_urls


queries = []
if is_(opts.file):
    queries.extend(get_words(opts.file, i=opts.start, j=opts.stop))
if is_(opts.query):
    queries.extend(opts.query)

for i, q in enumerate(queries):
    LOGGER.info('+++ QUERY #%s: %s +++\n' % (i, q))

    RESULT_DIR = osp.join(RESULT_PREFIX, q)
    mkdir_p(RESULT_DIR)

    if opts.load_urls:
        urls = read_lines(osp.join(opts.load_urls, q, 'urls.txt'))
    elif opts.sch:
        urls = image_search(q, opts.target)
        write_lines(urls, osp.join(RESULT_DIR, 'urls.txt'))

    if opts.load_preds:
        preds = read_lines(osp.join(opts.load_preds, q, 'preds.txt'))
    elif opts.rsch:
        preds = reverse_search_urls(q, *urls, lang=opts.target,
                                    n_img=opts.n_img)
        write_lines(preds, osp.join(RESULT_DIR, 'preds.txt'))

    # TODO
    # if opts.pred:
    #     for top_n in 1, 3, 5, 10, 20, 25:
    #         for use_lang in True, False:
    #             pred_filtered = filter_results(preds, q, lang=opts.lang)
    #             for p in pred_filtered:
    #                 print(p)

fh.close()