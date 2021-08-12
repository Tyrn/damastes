FROM python:3.9-slim

ARG user=procrustes project=py-procr src=py_procr

# Non-root user.
RUN useradd -ms /bin/bash "$user"
USER $user
WORKDIR /home/$user
ENV PATH=/home/$user/.local/bin:$PATH

# Source and project files.
RUN mkdir /home/$user/$project
WORKDIR /home/$user/$project
COPY $src ./$src/
COPY pyproject.toml ./
#COPY poetry.lock ./

# Build.
RUN pip install poetry --user && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev && \
    poetry build

CMD ["bash"]