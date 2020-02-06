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
                       libqt4-dev \
                       libyaml-dev \
                       pkg-config \
                       python \
                       python-dev \
                       swig \
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

# Gaia - https://github.com/MTG/gaia
RUN git clone https://github.com/MTG/gaia.git /tmp/gaia \
    && cd /tmp/gaia \
    && git checkout v2.4.5 \
    && ./waf configure --with-python-bindings \
    && ./waf \
    && ./waf install \
    && cd / && rm -r /tmp/gaia

RUN mkdir /code
RUN mkdir /gaia_index
WORKDIR /code

RUN adduser -q --gecos "" --disabled-password fsweb

COPY entrypoint.sh /usr/local/bin

COPY --chown=fsweb:fsweb requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=fsweb:fsweb . /code

ENTRYPOINT ["entrypoint.sh"]