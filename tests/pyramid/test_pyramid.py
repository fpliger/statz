import time, datetime, os
from mock import Mock
from statz import pyramid as sp


from pyramid.config import Configurator
from pyramid.events import NewRequest
from pyramid.events import subscriber
from pyramid.events import ApplicationCreated
from pyramid.httpexceptions import HTTPFound
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from pyramid.view import view_config


def test_includeme(monkeypatch):
    # tests environment setup
    fake_settings = {
        'A': 1,
        'B': 2,
        'statz.storage': 'json:///justapath'
    }
    extened_settings = {'C': 0}
    extened_settings.update(fake_settings)

    tracker_instance = Mock()
    parse_mock = Mock(return_value=fake_settings)
    monkeypatch.setattr(sp, 'parse_settings', parse_mock)
    monkeypatch.setattr(sp.storages, 'load', Mock())
    monkeypatch.setattr(sp, 'Tracker', Mock(return_value=tracker_instance))
    tracker_instance.handle_new_response = "handle_new_response"
    tracker_instance.handle_new_request = "handle_new_request"

    config = Mock()
    intr = Mock()
    config.introspection = intr
    config.registry.settings = fake_settings

    # actual call
    sp.includeme(config)

    # asserts...
    sp.parse_settings.assert_called_one_with(fake_settings)
    config.registry.settings == extened_settings

    # assert that the 2 functions that wrap pyramid request and responses
    # are being registered
    assert config.add_subscriber.call_count == 2
    config.add_subscriber.assert_any_call(
        "handle_new_response", sp.NewResponse
    )
    config.add_subscriber.assert_any_call(
        "handle_new_request", sp.NewRequest
    )

    # and the public views to serve the stats page have been added
    config.add_static_view.assert_any_call('statz/static', sp.STATIC_PATH)
    config.add_route.assert_any_call('statzboard', '/statzboard')

    # assert that the original config introspection attr hasn't been replaced
    assert config.introspection == intr

def test_parse_settings():
    settings = {
        "A": "any_value",
    }

    # in this case we don't specify any custom value so returned dict must
    # match the default_settings dict
    dsettings = dict([('statz.%s' % x[0], x[1](x[2])) \
                      for x in sp.default_settings])
    parsed = sp.parse_settings(settings)
    assert parsed == dsettings

    dsettings = dict([('statz.%s' % x[0], x[1](x[2])) \
                      for x in sp.default_settings])
    settings = {
        "A": "any_value",
        'statz.storage': 'json:///justapath',
    }
    dsettings['statz.storage'] = 'json:///justapath'
    parsed = sp.parse_settings(settings)
    assert parsed == dsettings

    dsettings = dict([('statz.%s' % x[0], x[1](x[2])) \
                      for x in sp.default_settings])
    settings = {
        "A": "any_value",
        'statz.storage': 'json:///justapath',
        'statz.loggers': 'AnyNewTestLogger',
    }
    dsettings['statz.storage'] = 'json:///justapath'
    dsettings['statz.loggers'] = 'AnyNewTestLogger'
    parsed = sp.parse_settings(settings)
    assert parsed == dsettings

test_records = [{'id': n, 'name': 'test task %i!!' % n} for n in range(5)]

def create_app_config(tmpdir):
    """
    Uses pyramid tasks tutorial as base to create a 'realistic-ish' app config
    to use for traditional pyramid app testings
    """

    # define test app view functions
    # views
    @view_config(route_name='list', renderer='list.mako')
    def list_view(request):
        """
        Lists all open tasks
        """
        return {'tasks': test_records}


    @view_config(route_name='new', renderer='new.mako')
    def new_view(request):
        """
        Creates a new task.

        Parameters:

        name ::: (string) text describing the task
        """
        return {'tasks': test_records}


    @view_config(route_name='close')
    def close_view(request):
        """
        Closes a task
        """
        # this is a very dummy test fixture...
        return []


    @view_config(context='pyramid.exceptions.NotFound', renderer='notfound.mako')
    def notfound_view(request):
        request.response.status = '404 Not Found'
        return {}


    settings = {}
    settings['reload_all'] = True
    settings['debug_all'] = True
    settings['mako.directories'] = '%s' % tmpdir.join('templates')
    settings['statz.storage'] = "json://%s" % tmpdir

    # session factory
    session_factory = UnencryptedCookieSessionFactoryConfig('itsaseekreet')

    # configuration setup
    config = Configurator(settings=settings, session_factory=session_factory)

    # add mako templating
    config.include('pyramid_mako')
    config.include('statz.pyramid')

    # routes setup
    config.add_route('list', '/')
    config.add_route('new', '/new')
    config.add_route('close', '/close/{id}')

    # static view setup
    config.add_static_view('static', '%s' % tmpdir.join('static'))
    # scan for @view_config and @subscriber dec

    config.scan()
    # serve app
    app = config.make_wsgi_app()

    return config

class TestTracker(object):

    def test_init_tracker(self, tmpdir, monkeypatch):
        # monkeypatch some key methods that must be called to activate and
        # configure the tracker
        monkeypatch.setattr(sp.Tracker, 'init_session_id', Mock())
        monkeypatch.setattr(sp.Tracker, 'activate_loggers', Mock())

        # IMPORTANT: need to patch include me method to be sure it does not
        #            affect test results
        monkeypatch.setattr(sp, 'includeme', lambda x: x)

        storage_path = tmpdir.join('test_storage')
        storage = sp.storages.load(
            'json://%s' % storage_path
        )

        # IMPORTANT: this method callse config.scan() to actually load views
        #            callables. This means that it would implicitly affect
        #            this teest results if we wouldn't have patched it
        config = create_app_config(storage_path)

        # init a new tracker
        before = datetime.datetime.now()
        tracker = sp.Tracker(
            config=config,
        )
        after = datetime.datetime.now()

        # check that the application routes have been detected and saved
        assert 'ROOT' in tracker.stats
        assert 'new' in tracker.stats
        assert 'close__id' in tracker.stats

        # Check that the storage has been created and it's correct
        assert tracker.storage
        assert isinstance(tracker.storage, sp.storages.JsonStorage)
        assert tracker.storage.url == str(storage_path)

        tracker.activate_loggers.assert_called_once_with(None)
        tracker.init_session_id.assert_called_once_with()



