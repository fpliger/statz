from collections import defaultdict, OrderedDict
import resource
import time
import json
import re
import datetime
import inspect

from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.view import view_config
from pyramid.wsgi import wsgiapp2
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid.events import NewRequest, NewResponse
from pyramid.events import subscriber

from webhelpers.html import converters

from py.path import local

import storages
import loggers

from pprint import pprint

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

here = local(storages.__file__).dirpath()
SETTINGS_PREFIX = 'statz.'
STATIC_PATH = here.join('static')
DEFAULT_LOGGERS = 'MemoryLogger, TrafficLogger'

default_settings = [
    ('enabled', asbool, r'true'),
    ('storage', str, r'./statz/'),
    ('loggers', str, DEFAULT_LOGGERS),
    ('exclude_paths', str, r"^/static*"),
]

class Tracker(object):
    default_excluded_paths = set([r"^/statz*", r"^statz*"])

    def __init__(self, config=None, storage=None, active_loggers_str=None):
        self.init_session_id()

        # create stats dict to store live stats info about views
        self.stats = {}

        # flag that indicates if routes have been loaded from config at least
        # once
        self.loaded_routes = False

        self.activate_loggers(active_loggers_str)

        self.storage = storage
        self.excluded_paths = set(Tracker.default_excluded_paths)

        # if config has been passed we can use it to load all declared routes
        if config:
            self.init_from_config(config)

        # if the storage wasn't created explicitly from parameters of from the
        # received config then we need to create a dummy storage
        if not self.storage:
            self.storage = storages.MockStorage()

    def init_from_config(self, config, overwrite_storage=False):
        """
        Inits storage, excluded_paths from configurations settings and
        parses config to load all it's configured routes

        Parameters:

        config              ::: Pyramid config object
        overwrite_storage   ::: (bool) if True forces to re-define the instance
                                storage
        """
        # before any other thing we must check if the storage has been set
        # otherwise we cannot load (and store) the routes from the config
        if overwrite_storage or not self.storage:
            self.create_storage_from_settings(config.registry.settings)

        # define paths to exclude before loading routes so we know which ones
        # to exclude
        self.exclude_paths_from_settings(config.registry.settings)

        # finally get settings dict from the config object and load it's routes
        settings = config.registry.settings
        self.load_routes_from_config(config)

    def exclude_paths(self, paths):
        """
        Adds the specified paths to the tracker excluded paths

        Parameters:

        paths   ::: (iterable) list (or any iterable) of path strings that must
                    be excluded when tracker intercepts and saves into about a
                    new request/response
        """
        self.excluded_paths.update(paths)

    def exclude_paths_from_settings(self, settings):
        """
        Searches for statz specific excluded_paths key on a settings dictionary.
        If the statz.excluded_paths key is found it is used to add those paths
        to the tracker excluded paths.

        Parameters:

        settings    ::: configuration dictionary

                        i.e.:
                        {'statz.exclude_paths': ''^/statics*, anystring''}

        """
        excluded_paths = settings.get(
            '%s%s' % (SETTINGS_PREFIX, 'exclude_paths'),
            ''
        )
        if excluded_paths:
            paths = [x.strip() for x in excluded_paths.split(',')]
            self.exclude_paths(paths)


    def create_storage_from_settings(self, settings):
        """
        Searches for statz specific storage definition on a settings dictionary
        If the statz.storage key is found it is used to configure the tracker
        storage object.

        Parameters:

        settings    ::: configuration dictionary
                        i.e.:
                        {'statz.storage': 'json:///some/path/'}



        """
        self.storage = storages.load(
            settings['%s%s' % (SETTINGS_PREFIX, 'storage')]
        )

    def init_session_id(self):
        """
        Initializes the tracker session id number
        """
        now = datetime.datetime.now()
        self.session = now.strftime('%Y%m%d%H%M%S')

    def parse_loggers_str(self, loggers_config_str):
        """
        Receives a loggers configuration string (a simple string with the
        names of the loggers to use separated by ',') and returns the list
        of the strings matching the loggers class names.
        """
        return [x.strip() for x in loggers_config_str.split(',')]

    def activate_loggers(self, active_loggers_str):
        """
        Receives a loggers configuration string (a simple string with the
        names of the loggers to use separated by ',') and initializes them
        on instance object level.
        """
        if active_loggers_str is None:
            active_loggers_str = DEFAULT_LOGGERS

        self._loggers = []
        self.loggers = self.parse_loggers_str(active_loggers_str)

        for logger in self.loggers:
            logger = getattr(loggers, logger)
            self._loggers.append(logger())


    def take_path(self, path):
        """
        Checks the instance 'exclude_paths' attributes and decides if the path
        statistics must be registred or not. Method uses regex.match to check
        matches of path and configured paths to exclude in 'exclude_paths'
        """
        for p in self.excluded_paths:
            if re.match(p, path, re.M|re.I):
                return False

        return True

    def parse_cornice_service(self, url, serv, path_stats = None):
        """
        Parses a cornice service definition and returns a dict with information
        about the service:

        Parameters

        - url       ::: url route of the service
        - service   ::: cornice service

        Output:

        a dict with thefollowing structure:

        - url       ::: url route of the service
        - methods   ::: dict with service defined methods as keys and a dict
                        with the following structure as values:

                        - callable  ::: view python callable object
                        - code      ::: callable source code prettified and
                                        converted to html friendly syntax with
                                        pygments
                        - docstring ::: callable docstring
                        - calls     ::: list that contains tracked calls for
                                        that specific METHOD and URL
        """
        #url = serv.path
        nurl = self.normalize_url(url)

        if self.take_path(url):

            # load any previously saved stats for this route or initialize
            # a new stats dictionary
            if not path_stats:
                path_stats = self.storage.load(nurl)

            if not 'url' in path_stats:
                path_stats['url'] = url

            if not 'methods' in path_stats:
                path_stats['methods'] = {}
                path_stats['methods_with_stats'] = []

            psts = path_stats['methods']
            for (method, view, args) in serv.definitions:
                foo = getattr(args['klass'], view)

                try:
                    docstring = converters.format_paragraphs(
                                inspect.getdoc(foo), True
                            )
                except:
                    docstring = ''

                try:
                    source = inspect.getsource(foo)
                    source = highlight(source, PythonLexer(), HtmlFormatter())

                except:
                    source = ''

                psts_meth = psts.get(method, {'calls': []})

                psts_meth.update({
                    'docstring': docstring,
                    'callable': '%s.%s' % (args['klass'], view),
                    'code': source
                })
                psts[method] = psts_meth

            self.storage.save(nurl, path_stats)

            # Add the path to the current global live stats
            self.stats[nurl] = path_stats


    def load_route(self, route):
        path = route['introspectable']['pattern']

        if self.take_path(path):

            # normalized path used to save the eventual route json (if the
            # configured storage don't support some url chars (like '/' for
            # JsonStorages
            npath = self.normalize_url(path)

            if npath not in self.stats:

                # load any previously saved stats for this route or initialize
                # a new stats dictionary
                path_stats = self.storage.load(npath)

                # it url is not registered for this routes it means it's the
                # the first time we register it. So we need to configure it's
                # url and save it for the next time
                if not 'url' in path_stats:
                    path_stats['url'] = path

                if not 'methods' in path_stats:
                    path_stats['methods'] = {}
                    path_stats['methods_with_stats'] = []

                for rel in route['related']:
                    foo = rel['callable']
                    docstring = converters.format_paragraphs(
                        inspect.getdoc(foo), True
                    )

                    try:
                        source = inspect.getsource(foo)
                        source = highlight(source, PythonLexer(), HtmlFormatter())
                    except TypeError:
                        source = ''

                    if rel['request_methods']:
                        path_stats['methods'][rel['request_methods']] = {
                            'code': source,
                            'docstring': docstring,
                            'callable': foo.__name__,
                            'calls': []
                        }

                    elif len(route['related']) == 1:
                        # in this case there's no specific method specified
                        # on this related. We can assume that this related
                        # view is used for all verbs

                        path_stats['methods']['ALL'] = {
                            'code': source,
                            'docstring': docstring,
                            'callable': foo.__name__,
                            'calls': []
                        }

                self.storage.save(npath, path_stats)

                # Add the path to the current global live stats
                self.stats[npath] = path_stats

    def load_cornice_routes(self):
        try:
            from cornice import service

            for serv in service.SERVICES:
                path = serv.path
                npath = self.normalize_url(path)

                if self.take_path(path):
                    # Parse the cornice service again to update service info
                    # if there was any change to the code or docstrings
                    self.parse_cornice_service(path, serv)

        except ImportError:
            # in this case cornice is not installed. We cannot use it
            pass

    def load_pyramid_standard_routes(self, config):
        # Parse all routes registered directly from the pyramid config object
        introspector = config.introspector
        routes = introspector.get_category('routes')
        if routes:
            for x in routes:
                self.load_route(x)

            self.loaded_routes = True

    def load_routes_from_config(self, config):
        """
        Receives a pyramid config object and infers its configured routes
        from it's introspector attributes. Routes found are initialized and
        pre-saved (at the configured instance storage object) before actually
        start saving any statistics of those. This should provide a complete
        list of routes configured and registered at the config object.
        """
        # Before getting everything from Pyramid let's check if user is using
        # cornice and get info from there as it's more complete and we can
        # actually have access to more details (like views doc strings to use
        # as methods documentation
        self.load_cornice_routes()

        self.load_pyramid_standard_routes(config)

    def get_request_path(self, request, normalize=False):
        """
        Receives a request and returns its route path.

        Inputs:

        request     ::: Pyramid request object
        normalize   ::: if True the returned route path is normalized
                        using the normalize_url methor before being returned
        """
        if request.matched_route:
            url = request.matched_route.pattern

        else:
            url = request.path

        if normalize:
            url = self.normalize_url(url)

        return url

    @staticmethod
    def normalize_url(url):
        """
        Normalizes the url path stripping annoying characters [that are not
        filename and html id friendly]
        """
        to_clean = [('}', ''), ('/', '_'), ('{', '_'), ('*', '<all>')]
        if url.startswith('/'):
            url = url[1:]
            if not url:
                url = 'ROOT'

        for x, y in to_clean:
            url = url.replace(x, y)

        return url

    def handle_new_request(self, event):
        """
        Intercepts a new request creation and defines single request statistics
        used to metric time and performance.
        """
        if not self.loaded_routes:
            self.load_routes_from_config(event.request.registry)

        req = event.request
        _id = repr(req)
        if _id in self.stats:
            raise EnvironmentError('Duplicated request!')

        call_stats = {}

        url = self.get_request_path(event.request)
        if self.take_path(url):
            call_stats = {
                "session": self.session,
                "url": url,
                "method": req.method,
                "timestamp": time.time(),
                "duration": -1,
                'headers': dict(req.headers),
            }
            self._handle_new_request(event, call_stats)
            self.stats[_id] = call_stats

    def _handle_new_request(self, event, call_stats):
        for logger in self._loggers:
            logger.handle_request(event, call_stats)

    def handle_new_response(self, event):
        _id = repr(event.request)

        url = self.get_request_path(event.request)
        nurl = self.normalize_url(url)
        if self.take_path(url):
            call_stats = self.stats[_id]
            meth = call_stats['method']
            path_stats = self.stats.get(nurl, None)

            if path_stats is None:
                path_stats = self.storage.load(nurl)
                path_stats['url'] = url

            if not 'methods' in path_stats:
                path_stats['methods'] = {}
                path_stats['methods_with_stats'] = []

            if not meth in path_stats['methods']:
                if 'ALL' in path_stats['methods']:
                    meth = 'ALL'

                if not path_stats.get('methods', {}):
                    path_stats['methods'] = {
                        meth: {
                            'code':'',
                            'docstring': 'PATH MISSED FROM AUTODISCOVER',
                            'callable': '---',
                            'calls': [],
                            'headers': '',
                        },
                    }

            call_stats['duration'] = \
                    (time.time() - call_stats['timestamp']) * 1000

            # track response json_body if content-type is json
            if 'json' in event.response.content_type:
                try:
                    call_stats['response_json_body'] = event.response.json_body

                except ValueError, e:
                    call_stats['response_json_body'] = '<error decoding json object>'
            else:
                call_stats['response_json_body'] = 'n.a.'

            self._handle_new_response(event, call_stats)

            try:
                calls = path_stats['methods'][meth]['calls']
                calls.append(call_stats)
                path_stats['methods'][meth]['calls'] = calls

                if not meth in path_stats['methods_with_stats']:
                    path_stats['methods_with_stats'].append(meth)

            except KeyError:
                print "OOOOOPS, something went wrong registering", meth, url

            self.stats[nurl] = path_stats
            self.storage.save(nurl, path_stats)

            return call_stats

    def _handle_new_response(self, event, call_stats):
        for logger in self._loggers:
            logger.handle_response(event, call_stats)


class Board(object):
    default_folder = None
    def __init__(self, request, folder=None):
        self.routes = OrderedDict()

        if folder or self.default_folder:
            self.load_path(folder or self.default_folder)

    def load_path(self, path):
        statsdir = local(path)
        for jsonfile in statsdir.listdir('*.json'):
            with jsonfile.open('r') as fp:
                key = Tracker.normalize_url(jsonfile.purebasename)
                self.routes[key] = json.load(fp)

    @view_config(
        route_name='statzboard',
        permission=NO_PERMISSION_REQUIRED,
        renderer='statz.pyramid.views:templates/dashboard.mako',
        )
    def view_stats(self):
        def fmt(col, val):
            if col == 'timestamp':
                return datetime.datetime.fromtimestamp(val).strftime('%Y-%m-%d %H:%M:%S')

            elif col == 'memory' and isinstance(val, float):
                return "%.3f MB" % val

            elif col == 'duration' and isinstance(val, float):
                return "%.3f s" % val

            return val

        return {
            'routes': self.routes,
            'fmt': fmt,
            'render_key_value_table': render_key_value_table,
            'render_stats_plot': render_stats,
        }

    def export(self, path, exclude_keys=None):
        if exclude_keys is None:
            exclude_keys = set()
        out = []

        for k, v in self.routes.items():
            calls = v.get('calls', [])
            upath = v.get('url', k.replace('_', '/'))

            if calls:
                cols = [k for k in v['calls'][0].keys() if k not in exclude_keys]
                txtcols = u';'.join(cols)

                out.append(upath + ';' + cols)

            else:
                out.append(upath)

            for call in calls:
                out.append(u';' + (u';'.join(repr(x) for k, x in \
                                      call.items() if k not in exclude_keys))
                )

            out.append(u'')

        path = local(path)
        path.write(u'\n'.join(out))

def parse_settings(settings):
    """
    Parse setting dict configuration, check if it defines any statz related
    values and return a dict with stats related settings. Useing custom values
    if specified or those in default_settings otherwise.
    """
    parsed = {}

    def populate(name, convert, default):
        name = '%s%s' % (SETTINGS_PREFIX, name)
        value = convert(settings.get(name, default))
        parsed[name] = value

    # Extend the ones we are going to transform later ...
    #default_settings.extend(default_transform)
    for name, convert, default in default_settings:
        populate(name, convert, default)
    return parsed

def includeme(config):
    """
    Activates statz pyramid plugin

    This can be called via config.include('statz.pyramid') or adding
    statz.pyramid in the pyramid.includes configuration. For more info
    on how this works refer to Pyramid documentation
    """
    introspection = getattr(config, 'introspection', True)
    # dont register any introspectables for Pyramid 1.3a9+
    config.introspection = False

    # Parse the settings
    settings = parse_settings(config.registry.settings)

    # Update the current registry with the new settings that could have been
    # added with the defaults in case there where not explicitly included in
    # the config file
    config.registry.settings.update(settings)

    tracker = Tracker(config=config)

    # TODO: Need this? If so, should make it more pythonic...
    Board.default_folder = tracker.storage.url

    # subscribe the 2 wrapper functions that will log all info configured
    config.add_subscriber(tracker.handle_new_response, NewResponse)
    config.add_subscriber(tracker.handle_new_request, NewRequest)

    # add views that can be used to read collected info
    config.add_static_view('statz/static', str(STATIC_PATH))
    config.add_route('statzboard', '/statzboard',)

    config.scan('statz.pyramid')
    config.introspection = introspection

    print "Statz plugin active"

    # TODO: We should create a brand new application that self contains statz


def render_key_value_table(id, values, klass="table table-striped", style="display:none;"):
    templ = u"""
<table id="%(id)s" class="%(klass)s" style="%(style)s">
  <thead>

    <tr>
            <th>name</th>
            <th>value</th>
    </tr>
  </thead>
  <tbody>
   %(values_)s
  </tbody>
</table>
"""

    templ_tr = u"""<tr>
  <td>%s</td>
  <td>%s</td>
</tr>"""
    values_ = u""

    if not values:
        values = {'no value': 'no value'}

    elif isinstance(values, list) :
        values = values[0]

    for col, val in values.items():
        values_ += templ_tr % (col, render_table_value(val))

    table = templ % locals()

    return table

def render_table_value(val):
    #TODO: make this function handle list values so it returns a summary version of the value
    return val

def render_stats(url, stats, method):
    import vincent

    if 'calls' in stats:
        calls = stats['calls']
        data = [x['duration'] for x in calls]

        if data:
            line = vincent.Line(data)
            line.axis_titles(x='%s %s' % (method, x['url']), y='Duration')
            filepath = STATIC_PATH.join("assets", "%s_%s.json" % (method, url))

