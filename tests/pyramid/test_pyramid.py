from mock import Mock
from statz import pyramid


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
    monkeypatch.setattr(pyramid, 'parse_settings', parse_mock)
    monkeypatch.setattr(pyramid.storages, 'load', Mock())
    monkeypatch.setattr(pyramid, 'Tracker', Mock(return_value=tracker_instance))
    tracker_instance.handle_new_response = "handle_new_response"
    tracker_instance.handle_new_request = "handle_new_request"

    config = Mock()
    intr = Mock()
    config.introspection = intr
    config.registry.settings = fake_settings

    # actual call
    pyramid.includeme(config)

    # asserts...
    pyramid.parse_settings.assert_called_one_with(fake_settings)
    config.registry.settings == extened_settings
    pyramid.storages.load.assert_called_once_with(
        fake_settings['statz.storage']
    )

    # assert that the 2 functions that wrap pyramid request and responses
    # are being registered
    assert config.add_subscriber.call_count == 2
    config.add_subscriber.assert_any_call(
        "handle_new_response", pyramid.NewResponse
    )
    config.add_subscriber.assert_any_call(
        "handle_new_request", pyramid.NewRequest
    )

    # and the public views to serve the stats page have been added
    config.add_static_view.assert_any_call('statz/static', pyramid.STATIC_PATH)
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
                      for x in pyramid.default_settings])
    parsed = pyramid.parse_settings(settings)
    assert parsed == dsettings

    dsettings = dict([('statz.%s' % x[0], x[1](x[2])) \
                      for x in pyramid.default_settings])
    settings = {
        "A": "any_value",
        'statz.storage': 'json:///justapath',
    }
    dsettings['statz.storage'] = 'json:///justapath'
    parsed = pyramid.parse_settings(settings)
    assert parsed == dsettings

    dsettings = dict([('statz.%s' % x[0], x[1](x[2])) \
                      for x in pyramid.default_settings])
    settings = {
        "A": "any_value",
        'statz.storage': 'json:///justapath',
        'statz.loggers': 'AnyNewTestLogger',
    }
    dsettings['statz.storage'] = 'json:///justapath'
    dsettings['statz.loggers'] = 'AnyNewTestLogger'
    parsed = pyramid.parse_settings(settings)
    assert parsed == dsettings

