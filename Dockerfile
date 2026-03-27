FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install build deps, runtime deps, and LaTeX in one layer
# Build-only packages are removed after pip install to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build dependencies (removed after pip install)
    build-essential \
    python3-dev \
    pkg-config \
    meson \
    ninja-build \
    # Runtime dependencies
    python3 \
    python3-pip \
    libcairo2-dev \
    libpango1.0-dev \
    ffmpeg \
    # LaTeX packages for mathematical typesetting
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    texlive-xetex \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir pycairo manim "mcp[cli]" \
    && python3 -c "import manim; print(f'Manim {manim.__version__} installed successfully')" \
    # Remove build-only packages
    && apt-get purge -y --auto-remove \
        build-essential \
        python3-dev \
        pkg-config \
        meson \
        ninja-build \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /root/.cache

WORKDIR /manim

COPY ./app /manim/app

ENTRYPOINT ["python3", "/manim/app/main.py"]
