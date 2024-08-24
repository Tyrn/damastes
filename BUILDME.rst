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
    $ pip install dist/<...>.whl --user [-I]

or, preferably

::

    $ pipx install dist/<...>.whl

Use Git Hooks
-------------

::

    $ poetry shell
    (.venv) $ pre-commit install
    ...
    (.venv) $ pre-commit run --all-files

Format
------

::

    $ poetry shell
    (.venv) $ black .

or

::

    $ poetry run black .

Test
----

::

    $ poetry shell
    (.venv) $ pytest [--doctest-modules] [-v]
    (.venv) $ mypy .

Poetry shell
------------

To exit Poetry shell press **Ctrl+D**

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
