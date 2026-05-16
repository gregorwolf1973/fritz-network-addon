ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3 py3-pip bash curl

RUN pip3 install --break-system-packages \
        influxdb==5.3.2 \
        fritzconnection==1.13.2 \
        requests==2.32.3

COPY app/ /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /app
CMD ["/run.sh"]
