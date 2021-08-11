Using this application with Docker
**********************************

Raw
===

Build
-----

::

    $ docker build -t procrustes --rm .

Run
---

::

    $ docker run -it --name procrustes --rm --mount type=bind,source="$HOME"/,target=/home/mnt procrustes

- `--name procrustes` is the container name; tailing/`target` `procrustes` is the image name.

Docker Compose
==============

Configuration
-------------

`.env`:

::

    HOST=$HOME

`docker-compose.yml`:

::

    services:
      tweaker:
        image: procrustes:latest
        volumes:
          - type: bind
            source: $HOME
            target: /home/mnt
        working_dir: /home/mnt

Run
---

::

    $ docker-compose run --rm procrustes