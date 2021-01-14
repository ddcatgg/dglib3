# -*- coding: utf-8 -*-
import os
import json
import pickle
import codecs
import collections.abc
from functools import wraps

from dglib3.utils import makesure_dirpathexists

FORMAT_JSON = 1
FORMAT_PICKLE = 2
FORMAT_TXT = 3


class FileCache(object):
    def __init__(self):
        self.enabled = True
        self.load_enabled = True
        self.save_enabled = True
        self.cache_set_name = ''
        self.base_dir = ''

    def cache(self, filename, cache_format=None, list_apply=None):
        filename = self.get_final_cache_filename(filename)

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if self.enabled and self.load_enabled:
                    if os.path.isfile(filename):
                        return self.load_cache(filename, cache_format, list_apply)

                result = func(*args, **kwargs)
                if self.enabled and self.save_enabled:
                    self.save_cache(result, filename, cache_format)
                return result

            return wrapper

        return decorator

    def guess_file_cache_format(self, filename):
        base, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext == '.json':
            cache_format = FORMAT_JSON
        elif ext == '.txt':
            cache_format = FORMAT_TXT
        else:
            cache_format = FORMAT_PICKLE
        return cache_format

    def load_cache(self, filename, cache_format, list_apply=None):
        if cache_format is None:
            cache_format = self.guess_file_cache_format(filename)

        if cache_format == FORMAT_JSON:
            with codecs.open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif cache_format == FORMAT_PICKLE:
            with open(filename, 'rb') as f:
                return pickle.load(f)
        elif cache_format == FORMAT_TXT:
            with codecs.open(filename, 'r', encoding='utf-8') as f:
                result = list(filter(None, map(lambda x: x.strip('\r'), f.read().split('\n'))))
                if list_apply is not None:
                    result = list(map(list_apply, result))
                return result

    def save_cache(self, cache, filename, cache_format):
        if cache_format is None:
            cache_format = self.guess_file_cache_format(filename)

        makesure_dirpathexists(filename)

        if cache_format == FORMAT_JSON:
            with codecs.open(filename, 'w', encoding='utf-8') as f:
                json.dump(cache, f)
        elif cache_format == FORMAT_PICKLE:
            with open(filename, 'wb') as f:
                return pickle.dump(cache, f, pickle.HIGHEST_PROTOCOL)
        elif cache_format == FORMAT_TXT:
            if not (isinstance(cache, collections.abc.Sequence) and not isinstance(cache, (str, bytes))):
                raise TypeError('FORMAT_TXT can only apply to sequence types, but got %r' % type(cache))
            with codecs.open(filename, 'w', encoding='utf-8') as f:
                return f.write('\r\n'.join(map(str, cache)))

    def get_final_cache_filename(self, filename):
        if self.cache_set_name:
            filename = os.path.join(self.base_dir, 'cache', self.cache_set_name, filename)
        else:
            filename = os.path.join(self.base_dir, 'cache', filename)

        base, ext = os.path.splitext(filename)
        if not ext:
            return ''.join([filename, '.cache'])
        return filename
