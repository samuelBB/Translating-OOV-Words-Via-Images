#!/usr/bin/env python3.7
from utils import arg, parse_args
from image_search import image_search
from reverse_image_search import reverse_search_urls

opts = parse_args(
    arg('-q', '--query'),
    arg('-t', '--target', default='en'),
    arg('-n', '--n-img',  type=int, default=3),
    arg('-d', '--debug', action='store_true'),
)

urls  = image_search(opts.query, opts.target, debug=opts.debug)
preds = reverse_search_urls(opts.query, *urls, opts.target,
                            opts.n_img, opts.debug)
print(preds)