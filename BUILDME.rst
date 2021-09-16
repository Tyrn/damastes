Damastes a.k.a. Procrustes
**************************

Build and install
=================

::

    $ poetry build

Exit venv or poetry shell, then:

::

    $ pip install dist/<...>.whl --user [-I]

Use Git Hooks
=============

::

    $ pre-commit install
    ...
    $ pre-commit run --all-files

Format
======

::

    $ black .

Test
====

::

    $ pytest [--doctest-modules] [-v]
    $ mypy .
    $ twine check dist/<...>.whl

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
