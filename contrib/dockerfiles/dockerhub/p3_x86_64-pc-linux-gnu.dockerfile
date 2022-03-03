ARG VERSION=latest
FROM defiwallet.azurecr.io/defichain-base:$VERSION as dh-build

FROM debian:10-slim
ENV PATH=/app/bin:$PATH
WORKDIR /app

COPY --from=dh-build /app/. ./

RUN useradd --create-home defi && \
    mkdir -p /data && \
    chown defi:defi /data && \
    ln -s /data /home/defi/.defi

VOLUME ["/data"]

USER defi:defi
CMD [ "/app/bin/defid" ]
ENTRYPOINT [ "/app/bin/defid" ]