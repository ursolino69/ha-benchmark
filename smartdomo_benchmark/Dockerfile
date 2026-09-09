ARG BUILD_FROM=ghcr.io/home-assistant/home-assistant:2026.9.1
FROM ${BUILD_FROM}

WORKDIR /app
COPY app/ /app/
COPY run.sh /run.sh
RUN chmod a+x /run.sh

EXPOSE 8099
ENTRYPOINT []
CMD ["/run.sh"]
