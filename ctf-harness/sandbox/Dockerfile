# Executor image: the toolbox the agent gets inside the sandbox.
# Build once:  docker build -t ctf-harness-sandbox:latest sandbox/
#
# Kept deliberately lean but covers the common CTF categories. Add tools as your
# platform's challenges demand (the agent can also pip/apt-install at runtime IF
# network_mode allows it — with network_mode: none it's stuck with what's here).
FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    # general
    bash coreutils file xxd less nano vim-tiny jq unzip zip tar gzip \
    build-essential gcc g++ make \
    # networking (usable only when network_mode allows it)
    netcat-openbsd curl wget socat \
    # crypto
    openssl \
    # reverse engineering / pwn
    gdb binutils ltrace strace radare2 \
    # forensics / stego
    binwalk foremost exiftool steghide outguess tcpdump \
    # misc
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Python CTF staples
RUN pip install --no-cache-dir \
    pwntools \
    pycryptodome \
    requests \
    sympy \
    gmpy2 \
    z3-solver \
    capstone \
    unicorn

WORKDIR /work
CMD ["sleep", "infinity"]
