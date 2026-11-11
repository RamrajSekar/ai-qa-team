# Build context: visual-runner only. No API, .env, credentials or local artifacts.
FROM python:3.12.12-slim-bookworm
ARG CFT_VERSION=146.0.7680.31
RUN test "$(dpkg --print-architecture)" = amd64 \
 && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl unzip tini fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 \
    libglib2.0-0 libgtk-3-0 libnspr4 libnss3 libpango-1.0-0 \
    libx11-6 libxcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxkbcommon0 libxrandr2 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /runner
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir pip==25.0.1 \
 && python -m pip install --no-cache-dir -r requirements.txt && python -m pip check
RUN mkdir -p /opt/cft \
 && curl --fail --location --proto '=https' "https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chrome-linux64.zip" -o /tmp/chrome.zip \
 && curl --fail --location --proto '=https' "https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chromedriver-linux64.zip" -o /tmp/driver.zip \
 && unzip -q /tmp/chrome.zip -d /opt/cft && unzip -q /tmp/driver.zip -d /opt/cft \
 && /opt/cft/chrome-linux64/chrome --version | grep -F "$CFT_VERSION" \
 && /opt/cft/chromedriver-linux64/chromedriver --version | grep -F "$CFT_VERSION" \
 && chown root:root /opt/cft/chrome-linux64/chrome_sandbox \
 && chmod 4755 /opt/cft/chrome-linux64/chrome_sandbox \
 && rm /tmp/chrome.zip /tmp/driver.zip \
 && useradd --uid 10001 --create-home runner \
 && mkdir /output && chown runner:runner /output
COPY lab/ ./lab/
COPY linux/ ./linux/
RUN python -m linux.check_dependencies
RUN python -c "import json; from linux.contract_validation import validate_manifest; validate_manifest({'schema_version':'1.0','batch_id':'a'*32,'adapter':'robot-direct-webdriver-batch-v1','mode':'mechanical-smoke','environment':'controlled-synthetic-v1','cases':[{'case_run_id':'b'*32,'specification':'synthetic-form-v1','authorization':'server-owned-fixture'}],'case_timeout_seconds':90,'batch_timeout_seconds':110})"
ENV PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
ENTRYPOINT ["/usr/bin/tini", "--", "python", "-m", "linux.entrypoint"]
