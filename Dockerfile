FROM python:3.10.1-slim-bullseye AS base

ARG user=damastes project=damastes src=src

# Non-root user.
RUN useradd -ms /bin/bash "$user"
USER $user
WORKDIR /home/$user
ENV PATH=/home/$user/.local/bin:$PATH

# Project.
RUN pip install poetry==1.4.0 --user && \
    mkdir /home/$user/$project
WORKDIR /home/$user/$project
COPY $src ./$src/
COPY pyproject.toml poetry.lock README.rst ./

# Build.
RUN poetry config virtualenvs.create true && \
    poetry install --no-dev && \
    poetry build -f sdist

FROM python:3.10.1-slim-bullseye

ARG user=damastes project=damastes

RUN apt-get update && \
    apt-get install -y tree && \
    apt-get install -y less && \
    apt-get install -y zoxide && \
    useradd -ms /bin/bash "$user"
# Non-root user.
USER $user
WORKDIR /home/$user
ENV PATH=/home/$user/.local/bin:$PATH

COPY --from=base /home/$user/$project/dist/ ./dist/
RUN pip install ./dist/* --user && \
    echo 'alias ll="ls -lh"' >> .bashrc && \
    echo 'alias lls="ls -lh --color=always | less -r"' >> .bashrc && \
    echo 'alias lss="ls --color=always | less -r"' >> .bashrc && \
    echo 'alias dm=damastes' >> .bashrc && \
    echo 'eval "$(zoxide init bash --hook=prompt)"' >> .bashrc && \
    echo 'alias cd=z' >> .bashrc

CMD ["bash"]
