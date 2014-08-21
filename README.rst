``statz``
========================

The initial idea behing ``statz`` is to provide a simple, small and easy to
use tool that integrates with web applications (Pyramid at first) and tests
tools (py.test) to provide project documentation and trivial debug information
over time. This tool is designed with a REST service in mind as consumer of
the tool but it should be friendly enough to be applied to any Pyramid project.

This should help project developers and teams to maintain an overview over
their web services, tests, documentation and performance.

Desired features (on the roadmap):

- API documentation: display the application routes and methods
- API performance: Tracks and register single calls performance (time and memory) over time
- API info: Tracks and register single calls info (basic request/response like headers,
payloads, status code, etc..) over time.
- Nice API documentation-like UI: Provide a nice looking UI that can be used as API overview
and documentation (possibly gathering enough information from views docstrings and infering
from tracked in/out info)
- Detect API changes: detect and show significant changes on performance or API design over time
in order to notify users of 'unexpected' changes.
- Detect Major performance changes: detect and show significant performance changes in service
calls should raise warnings


``statz.pyramid``
========================

``statz.pyramid`` provides a statz functionality for Pyramid web framework.

How is it different from ``pyramid_debugtoolbar``?

Statz is influenced by the great job done with ``pyramid_debugtoolbar``
[or ``django-debugtoolbar`` or ``flask-debugtoolbar``] but aims to provide
different functionality.

Statz aims to provide information and track data/changes over time. Altough it
could be used to display debug information during development [in a similar
but much more limited way ``*_debugtoolbar`` does] it main purpose is to provide
a long term tool to improve project quality, documentation and overall overview
instead of more focused debug and tunning.

Documentation
-------------
TODO

Quick Start
-------------

...

- Create a virtualenv::

  >> virtualenv --system-site-packages ./statzenv

- Activate the virtual env::

  >> source ./statzenv/bin/activate

- Install Pyramid into the virtualenv::

  >> pip install pyramid

- Clone the ``statz`` trunk::

  >> git clone https://github.com/fpliger/statz.git

- Install the ``statz`` trunk into the virtualenv::

  >> cd statz
  >> python setup.py develop

- Create your amazing pyramid application!! If you don't have one yet you can use the demo one :-)

  >> cd statz/demo

- Include statz.pyramid in your project pyramid file adding 'statz.pyramid' to your includes list and
adding the statz.storage configuraiton. For example::

  # pyramid inludes
  pyramid.includes =
    ...
    statz.pyramid

  # statz storage folder configuration. This is where your json stats files will be saved
  statz.storage = json:///path/to/folder/

- Run your project as usual::

Now you can access the statz relative link /statzboard and see your project routes configuration.