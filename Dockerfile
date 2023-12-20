# mittaridatapumppu-persister

FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN addgroup -S app && adduser -S app -G app
WORKDIR /home/app

# Install requirements to build aiokafka
RUN apk add --no-cache \
  gcc \
  python3-dev \
  libc-dev \
  zlib-dev

# Copy and install requirements only first to cache the dependency layer
COPY --chown=app:app requirements.txt .
RUN pip install --no-cache-dir --no-compile --upgrade -r requirements.txt

COPY --chown=app:app . .

# Support Arbitrary User IDs
RUN chgrp -R 0 /home/app && \
  chmod -R g+rwX /home/app

USER app

CMD ["python", "./kafka2influxdb.py"]
