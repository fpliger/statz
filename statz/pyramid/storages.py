from collections import defaultdict
import json

from pyramid.events import subscriber
from pyramid.events import BeforeRender
import pdb

from pyramid.events import NewRequest, NewResponse
from pyramid.events import subscriber
import time
from pprint import pprint
from py.path import local
import resource


class BaseStorage(object):
    def __init__(self, url):
        self.url = url
        self.storage = local(self.url).ensure(dir=True)

    def __str__(self):
        return self.url

    def __repr__(self):
        return self.url

    def save(self, url, stats):
        return self._save(url, stats)

    def _save(self, url, stats):
        raise NotImplementedError()

    def load(self, url):
        return self._load(url)

    def _load(self, url):
        raise NotImplementedError()

class MockStorage(BaseStorage):
    def __init__(self, url=None):
        self.url = ''

    def _save(self, url, stats):
        return

    def _load(self, url):
        return defaultdict(list)

class JsonStorage(BaseStorage):
    def __init__(self, url):
        self.url = url
        self.storage = local(self.url).ensure(dir=True)

    @staticmethod
    def normalize_url(url):
        if url.startswith('/'):
            url = url[1:]
        return url.replace('/', '_')

    def _save(self, url, stats):
        url = self.normalize_url(url)
        fileobj = self.storage.join('%s.json' % url)

        print 'saving to...', fileobj
        with file(str(fileobj), 'w') as ff:
            json.dump(stats, ff)

    def _load(self, url):
        url = self.normalize_url(url)
        fileobj = self.storage.join('%s.json' % url)

        if fileobj.exists():
            with file(str(fileobj), 'r') as ff:
                try:
                    stats = json.load(ff)

                except ValueError, e:
                    if "No JSON object could be decoded" in e.message:
                        return defaultdict(list)

            return stats

        else:
            return {}

DEFAULT_STORAGE = JsonStorage
STORAGES_MAP = {
    'json': JsonStorage,
    'mock': MockStorage,
}
SEPARATOR = '://'

def load(url):
    stype, url = url.split(SEPARATOR)

    storage_class = STORAGES_MAP.get(stype.lower(), DEFAULT_STORAGE)
    storage = storage_class(url)

    return storage