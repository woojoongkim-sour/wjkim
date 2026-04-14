FROM postgres:17

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    lsb-release \
    gnupg2 \
    build-essential \
    postgresql-server-dev-17 \
    && rm -rf /var/lib/apt/lists/*

# Install pgvector
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Install PGroonga from Groonga apt repository
RUN wget https://packages.groonga.org/debian/groonga-apt-source-latest-$(lsb_release --codename --short).deb \
    && dpkg -i groonga-apt-source-latest-$(lsb_release --codename --short).deb \
    && rm groonga-apt-source-latest-$(lsb_release --codename --short).deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    postgresql-17-pgdg-pgroonga \
    groonga-tokenizer-mecab \
    && rm -rf /var/lib/apt/lists/*

# Cleanup build deps
RUN apt-get purge -y --auto-remove build-essential postgresql-server-dev-17 \
    && rm -rf /var/lib/apt/lists/*
