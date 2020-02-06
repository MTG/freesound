FROM debian:10

MAINTAINER Freesound support@freesound.org

ENV PYTHONUNBUFFERED=1

# Debian 10 installs python 2.7 as the 'python' package.
# Double-check this if upgrading to a new version of debian
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
                       build-essential \
                       ca-certificates \
                       git \
                       gosu \
                       pkg-config \
                       python \
                       python-dev \
                       wget \
    && rm -rf /var/lib/apt/lists/*

# pip
ENV PYTHON_PIP_VERSION 20.0.2
RUN set -ex; \
	\
	wget -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'; \
	\
	python get-pip.py \
		--disable-pip-version-check \
		--no-cache-dir \
		"pip==$PYTHON_PIP_VERSION" \
	; \
	pip --version; \
	\
	find /usr/local -depth \
		\( \
			\( -type d -a \( -name test -o -name tests \) \) \
			-o \
			\( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
		\) -exec rm -rf '{}' +; \
	rm -f get-pip.py


RUN mkdir /code
RUN mkdir /tag_recommendation_models
WORKDIR /code

RUN adduser -q --gecos "" --disabled-password fsweb

COPY entrypoint.sh /usr/local/bin

COPY --chown=fsweb:fsweb requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# To avoid installation problems, csc-pysparse needs to be installed after the other packages in requirements.txt
# have been installed. Therefore we install it with a dedicated command here
RUN pip install csc-pysparse==1.1.1.4

COPY --chown=fsweb:fsweb . /code

ENTRYPOINT ["entrypoint.sh"]