FROM ghcr.io/astral-sh/uv:0.11.15 AS uv
FROM openporousmedia/opmreleases:2025.10

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
  libhdf5-dev freeglut3-dev git \
  && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

ENV UV_PYTHON_INSTALL_DIR=/opt/uv/python
ENV UV_CACHE_DIR=/opt/uv/cache


RUN uv python install 3.14 && \
  uv pip install --python 3.14 --system --break-system-packages git+https://github.com/cssr-tools/pycopm.git

RUN chown -R opm /opt/uv/cache

USER opm

