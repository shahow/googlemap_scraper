FROM public.ecr.aws/lambda/python:3.12

# --------------------------------------------------
# Environment
# --------------------------------------------------

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Chrome / ChromeDriver
ENV CHROME_BIN=/opt/chrome/chrome
ENV CHROMEDRIVER=/opt/chromedriver/chromedriver
ENV PATH="/opt/chrome:/opt/chromedriver:${PATH}"

# Lambda writable directory
ENV HOME=/tmp

# --------------------------------------------------
# System packages required by Chrome
# --------------------------------------------------

RUN dnf install -y \
    wget \
    unzip \
    \
    alsa-lib \
    atk \
    at-spi2-atk \
    at-spi2-core \
    cairo \
    cups-libs \
    dbus-libs \
    expat \
    fontconfig \
    freetype \
    glib2 \
    gtk3 \
    libX11 \
    libXcomposite \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libXrandr \
    libXtst \
    libdrm \
    libxcb \
    libxkbcommon \
    mesa-libgbm \
    nspr \
    nss \
    pango \
    \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# --------------------------------------------------
# Install Chrome for Testing + matching ChromeDriver
# --------------------------------------------------

RUN mkdir -p /opt/chrome /opt/chromedriver \
    && python - <<'PY'
import json
import urllib.request
import zipfile
import io
import os
import shutil

url = (
    "https://googlechromelabs.github.io/"
    "chrome-for-testing/last-known-good-versions-with-downloads.json"
)

print("Downloading Chrome for Testing version information...")

with urllib.request.urlopen(url) as response:
    data = json.load(response)

version = data["channels"]["Stable"]["version"]
downloads = data["channels"]["Stable"]["downloads"]

print("Chrome version:", version)

# Find Linux x86_64 Chrome
chrome_url = next(
    item["url"]
    for item in downloads["chrome"]
    if item["platform"] == "linux64"
)

# Find Linux x86_64 ChromeDriver
driver_url = next(
    item["url"]
    for item in downloads["chromedriver"]
    if item["platform"] == "linux64"
)

print("Chrome URL:", chrome_url)
print("ChromeDriver URL:", driver_url)

# Download Chrome
with urllib.request.urlopen(chrome_url) as response:
    chrome_zip = response.read()

with zipfile.ZipFile(io.BytesIO(chrome_zip)) as z:
    z.extractall("/tmp/chrome")

shutil.copytree(
    "/tmp/chrome/chrome-linux64",
    "/opt/chrome",
    dirs_exist_ok=True
)

# Download ChromeDriver
with urllib.request.urlopen(driver_url) as response:
    driver_zip = response.read()

with zipfile.ZipFile(io.BytesIO(driver_zip)) as z:
    z.extractall("/tmp/chromedriver")

shutil.copy(
    "/tmp/chromedriver/chromedriver-linux64/chromedriver",
    "/opt/chromedriver/chromedriver"
)

os.chmod("/opt/chromedriver/chromedriver", 0o755)

print("Chrome installed:")
print("/opt/chrome/chrome")

print("ChromeDriver installed:")
print("/opt/chromedriver/chromedriver")
PY

RUN chmod +x /opt/chrome/chrome && chmod +x /opt/chrome/chrome_crashpad_handler && chmod +x /opt/chromedriver/chromedriver

# --------------------------------------------------
# Install uv
# --------------------------------------------------

COPY --from=ghcr.io/astral-sh/uv:0.12.4 /uv /uvx /usr/local/bin/

# --------------------------------------------------
# Lambda application directory
# --------------------------------------------------

WORKDIR ${LAMBDA_TASK_ROOT}

# --------------------------------------------------
# Install Python dependencies with uv
# --------------------------------------------------

COPY pyproject.toml uv.lock ./

RUN uv export \
    --frozen \
    --no-dev \
	--no-emit-project \
    --format requirements.txt \
    --output-file /tmp/requirements.txt \
    && pip install \
    --no-cache-dir \
    -r /tmp/requirements.txt \
    --target ${LAMBDA_TASK_ROOT}

# --------------------------------------------------
# Copy application
# --------------------------------------------------

COPY . ${LAMBDA_TASK_ROOT}

# --------------------------------------------------
# Lambda handler
# --------------------------------------------------

CMD ["lambda_function.lambda_handler"]