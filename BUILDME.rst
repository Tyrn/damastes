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

    $ docker build -t damastes --rm .

Run
---

::

    $ docker run -it --name damastes --rm --mount type=bind,source="$HOME"/,target=/home/mnt damastes

- ``--name damastes`` is the container name; tailing ``target=/home/mnt damastes`` is the image name.

Docker Compose
==============

Configuration
-------------

*docker-compose.yml*:

::

    services:
      damastes:
        image: damastes:latest
        volumes:
          - type: bind
            source: $HOME
            target: /home/mnt
        working_dir: /home/mnt

Run
---

::

    $ docker-compose run --rm damastes
