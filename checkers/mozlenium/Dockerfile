FROM node:latest

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
	apt-transport-https \
	bzip2 \
	build-essential \
	ca-certificates \
	clang \
	dbus-x11 \
	dirmngr \
	fonts-dejavu \
	fonts-liberation \
	fonts-noto \
	fonts-lyx \
	gnupg \
	hicolor-icon-theme \
	libasound2 \
	libatk1.0-0 \
	libc6 \
	libcairo-gobject2 \
	libcairo2 \
	libcanberra0 \
	libdbus-1-3 \
	libdbus-glib-1-2 \
	libdbusmenu-glib4 \
	libdbusmenu-gtk4 \
	libfontconfig1 \
	libfreetype6 \
	libgcc1 \
	libgdk-pixbuf2.0-0 \
	libgl1-mesa-dri \
	libgl1-mesa-glx \
	libglib2.0-0 \
	libgtk-3-0 \
	libgtk2.0-0 \
	libpango-1.0-0 \
	libstartup-notification0 \
	libstdc++6 \
	libx11-6 \
	libx11-xcb1 \
	libxcb-shm0 \
	libxcb1 \
	libxcomposite1 \
	libxdamage1 \
	libxext6 \
	libxfixes3 \
	libxrender1 \
	libxt6 \
	locales \
	lsb-release \
	pulseaudio \
	pulseaudio-utils \
	software-properties-common \
	wget \
	xauth \
        --no-install-recommends \
        && apt-get clean

RUN wget -q -O nightly.tar.bz 'https://download.mozilla.org/?product=firefox-nightly-latest-ssl&os=linux64&lang=en-US' && \
    tar xjf nightly.tar.bz && \
    ln -s /app/firefox/firefox /usr/local/bin/firefox && \
    rm -f nightly.tar.bz

RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64]  http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get -y update && \
    apt-get -y install google-chrome-stable --no-install-recommends && \
    apt-get clean

RUN wget https://chromedriver.storage.googleapis.com/2.41/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    chown root:root chromedriver && \
    chmod +x chromedriver && \
    mv chromedriver /usr/bin/

ENV NODE_PATH /app/node_modules

COPY package.json mozlenium.js firefox-browser.js chrome-browser.js entrypoint.sh wrapper.js /app/

RUN npm install && \
    npm run install-chrome-dependencies && \
    npm run install-firefox-dependencies

ENTRYPOINT [ "/app/entrypoint.sh" ]

