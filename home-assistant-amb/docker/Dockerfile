FROM ghcr.io/home-assistant/home-assistant:2026.2.2

ARG ADAPTIVE_LIGHTING_VERSION=1.26.0
ARG HA_ILLUMINANCE_VERSION=5.7.0

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

# Add ha-illuminance
RUN cd /tmp \
    && wget -O ha-illuminance.zip https://github.com/pnbruckner/ha-illuminance/archive/refs/tags/${HA_ILLUMINANCE_VERSION}.zip \
    && unzip ha-illuminance.zip \
    && mv ha-illuminance-${HA_ILLUMINANCE_VERSION}/custom_components/illuminance ${CUSTOM_COMPONENTS_DIR} \
    && rm -rf /tmp/*
