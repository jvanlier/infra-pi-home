FROM ghcr.io/home-assistant/home-assistant:2026.7.0

ARG ADAPTIVE_LIGHTING_VERSION=1.30.1

# Setup alternative custom_components directory.
# Home Assistant expects this in /config/custom_components, but I want to mount the entire config
# directory. So I have a symlink in the mounted ./config/custom_components -> /custom_components.
ARG CUSTOM_COMPONENTS_DIR=/custom_components
RUN mkdir -p ${CUSTOM_COMPONENTS_DIR}

# Add adaptive lighting
RUN cd /tmp \
    && wget -O adaptive-lighting.zip https://github.com/basnijholt/adaptive-lighting/archive/refs/tags/v${ADAPTIVE_LIGHTING_VERSION}.zip \
	&& unzip adaptive-lighting.zip \
	&& mv adaptive-lighting-${ADAPTIVE_LIGHTING_VERSION}/custom_components/adaptive_lighting ${CUSTOM_COMPONENTS_DIR} \
	&& rm -rf /tmp/*

# Add Duux Fan Local (local control of Duux fans via MQTT-TLS broker hijack)
ARG DUUX_FAN_LOCAL_VERSION=2.0.1
RUN cd /tmp \
    && wget -O duux-fan-local.zip https://github.com/LouisR-git/duux-fan-local/archive/refs/tags/${DUUX_FAN_LOCAL_VERSION}.zip \
    && unzip duux-fan-local.zip \
    && mv duux-fan-local-${DUUX_FAN_LOCAL_VERSION}/custom_components/duux_fan_local ${CUSTOM_COMPONENTS_DIR} \
    && rm -rf /tmp/*

# Add apexcharts-card (Lovelace custom card - used by the inside vs outside temperature chart on the overview + climate dashboards)
ARG APEXCHARTS_CARD_VERSION=v2.1.2
RUN mkdir -p /www \
    && wget -O /www/apexcharts-card.js \
       https://github.com/RomRider/apexcharts-card/releases/download/${APEXCHARTS_CARD_VERSION}/apexcharts-card.js

# Add plotly-graph-card (Lovelace custom card for fan speed curve graph — numeric x-axis)
ARG PLOTLY_GRAPH_CARD_VERSION=v3.3.5
RUN wget -O /www/plotly-graph-card.js \
    https://github.com/dbuezas/lovelace-plotly-graph-card/releases/download/${PLOTLY_GRAPH_CARD_VERSION}/plotly-graph-card.js
