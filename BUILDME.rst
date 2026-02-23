Damastes a.k.a. Procrustes
**************************

User's take
===========

::

    uv tool install git+https://github.com/Tyrn/damastes

Development
===========

::

    uv build

::

    uv tool install dist/<...>.whl

Use Git Hooks
-------------

::

    $ source .venv/bin/activate
    (.venv) $ pre-commit install
    ...
    (.venv) $ pre-commit run --all-files

Format
------

*Probably, obsolete*

::

    $ source .venv/bin/activate
    (.venv) $ black .

Test
----

::

    $ source .venv/bin/activate
    (.venv) $ pytest [--doctest-modules] [-v]
    (.venv) $ mypy .

Publish
-------

*Probably, obsolete.* See `the docs <https://docs.astral.sh/uv/guides/package/#publishing-your-package>`__

::

    $ uv build
    $ twine check dist/<...>.whl

then

::

    $ uv run twine upload --repository-url https://test.pypi.org/legacy/ dist/*

Containerize
************

Docker
======

Build
-----

::

    $ yay -S docker-buildx
    $ docker buildx install

::

    $ docker build -t damastes [-f Procrustesfile] --rm .

*NB* 2023-02-28: Only *Procrustesfile* is under development!

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

Make persistent
---------------

::

    $ docker update --restart unless-stopped damastes

Save & load image
-----------------

::

    $ docker save -o image.tar ImageID-or-Name
    $ docker load -i image.tar

Docker Compose
==============

Run
---

::

    $ docker-compose up -d

also possible:

::

    $ docker-compose -f docker-compose.yml run --name damastes --rm damastes
