FROM python:3.10-slim-buster

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    libnss3 \
    libfontconfig1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libgconf-2-4 \
    libgbm-dev \
    libdrm-dev \
    libatspi2.0-0 \
    libappindicator3-1 \
    libxkbcommon-x11-0 \
    libdbus-glib-1-2 \
    libgdk-pixbuf2.0-0 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libglib2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libcups2 \
    libxcursor1 \
    libxinerama1 \
    libxrandr1 \
    libxrender1 \
    libxi6 \
    libxtst6 \
    libgconf-2-4 \
    libxkbfile1 \
    libsecret-1-0 \
    libvulkan1 \
    libva-drm2 \
    libva-x11-2 \
    libva2 \
    libvdpau1 \
    libegl1 \
    libgl1 \
    libgles2 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcb-present0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-shm0 \
    libxcb-render0 \
    libxcb-glx0 \
    libxcb-randr0 \
    libxcb-shape0 \
    libxcb-xkb1 \
    libxcb-keysyms1 \
    libxcb-image0 \
    libxcb-util1 \
    libxcb-icccm4 \
    libxcb-xrm0 \
    libxcb-res0 \
    libxcb-composite0 \
    libxcb-damage0 \
    libxcb-dpms0 \
    libxcb-dri2-0 \
    libxcb-ewmh2 \
    libxcb-glx0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-render0 \
    libxcb-res0 \
    libxcb-screensaver0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-util1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxcb-xrm0 \
    libxcb-xtest0 \
    libxcb-xv0 \
    libxcb-xvmc0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY . .

RUN mkdir -p monitor/cookies && chmod -R 777 monitor/cookies

CMD ["python", "bot/main.py"]


