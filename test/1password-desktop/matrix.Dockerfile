ARG BASE=debian:12
FROM ${BASE}
RUN useradd --create-home --uid 1100 --shell /bin/bash featuretest
COPY src /tests/src
COPY test /tests/test
RUN HOSTCLIGID=23456 ACCEPTRUNTIMEOVERRIDE=true _REMOTE_USER=featuretest bash /tests/src/1password-desktop/install.sh \
 && HOSTCLIGID=23456 ACCEPTRUNTIMEOVERRIDE=true _REMOTE_USER=featuretest bash /tests/src/1password-desktop/install.sh
ENV XDG_RUNTIME_DIR=/run/1password-desktop
CMD ["python3", "/tests/test/1password-desktop/test_container.py"]
