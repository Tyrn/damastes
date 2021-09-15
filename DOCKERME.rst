Using this application with Docker
**********************************

Raw
===

Build
-----

::

    $ docker build -t damastes --rm .

Run
---

::

    $ docker run -it --name damastes --rm --mount type=bind,source="$HOME"/,target=/home/mnt damastes

- `--name damastes` is the container name; tailing/`target` `damastes` is the image name.

Docker Compose
==============

Configuration
-------------

`docker-compose.yml`:

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
