Damastes a.k.a. Procrustes
**************************

User's take
===========

::

    $ pip install --user git+https://github.com/Tyrn/damastes.git

Development
===========

::

    $ poetry build

Exit venv or poetry shell, then:

::

    $ pip install dist/<...>.whl --user [-I]

Use Git Hooks
-------------

::

    $ pre-commit install
    ...
    $ pre-commit run --all-files

Format
------

::

    $ black .

Test
----

::

    $ pytest [--doctest-modules] [-v]
    $ mypy .

Publish
-------

::

    $ poetry build
    $ twine check dist/<...>.whl

then

::

    $ poetry run twine upload --repository-url https://test.pypi.org/legacy/ dist/*

or

::

    $ poetry config --list
    $ poetry config repositories.testpypi https://test.pypi.org/legacy/
    $ poetry publish -r testpypi

- Poetry issue `#742 <https://github.com/python-poetry/poetry/issues/742>`__

Containerize
************

Docker
======

Build
-----

::

    $ docker build -t damastes [-f Procrustesfile] --rm .

Run
---

::

    $ docker run -it --name damastes --rm --mount type=bind,source="$HOME"/,target=/enjoy --mount type=bind,source=/run/media,target=/run/media,bind-propagation=shared -w /enjoy damastes:latest

- ``--name damastes`` is the container name; ``damastes[:latest]`` is the image name.

Detach
------

- Detach and leave it running: ``C-p C-q``
- Detach and kill the container: ``exit`` or ``C-d``

Attach
------

::

    $ docker exec -it damastes bash

Docker Compose
==============

Run
---

::

    $ docker-compose up -d

also possible:

::

    $ docker-compose -f docker-compose.yml run --name damastes --rm damastes
