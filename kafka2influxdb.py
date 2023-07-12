import json
import logging
import os
from pprint import pformat

from influxdb_client.client.write_api import SYNCHRONOUS

from fvhiot.database.influxdb import create_influxdb_client, get_influxdb_args
from fvhiot.utils import init_script
from fvhiot.utils.data import data_unpack
from fvhiot.utils.kafka import get_kafka_consumer_by_envs

"""
Consume parsed data from Kafka and save it to InfluxDB V2 database.

Parsed data is expected to be in the following "well-known" "JSON timeseries"-like format:

parsed_data = {
    "header": {
        "columns": {
            "0": {"name": "co2"},
            "1": {"name": "rh"},
            "2": {"name": "temp"},
        },
        "end_time": "2023-07-11T10:43:51.442+00:00",
        "start_time": "2023-07-11T10:43:51.442+00:00",
    },
    "data": [
        {
            "f": {
                "0": {"v": 492},
                "1": {"v": 43},
                "2": {"v": 26.5},
            },
            "time": "2023-07-11T10:43:51.442+00:00",
        },
        {
            "f": {
                "0": {"v": 495},
                "1": {"v": 42},
                "2": {"v": 27.0},
            },
            "time": "2023-07-11T10:53:51.456+00:00",
        }
],
    "device": {
        "device_id": "B81758FFFE031234",
        # FIXME: this is incorrect format for device_metadata now
        "device_metadata": {"name": "Elsys ERS CO2 A81758FFFE035729", "parser_module": "fvhiot.parsers.elsys"},
        "device_state": {"state data": "is here"},
    },
    "meta": {
        "timestamp_parsed": "2023-07-11T10:43:52.080521+00:00",
        "timestamp_received": "2023-07-11T10:43:51.442000+00:00",
    },
    "version": "1.0",
}

Expected result in influxdb datapoint format:

influxdb_points = [
    {
        "measurement": "measurement_name",
        "tags": {"dev-id": "device_id"},
        "fields": {"co2": 492, "rh": 43, "temp": 26.5},
        "time": "2023-07-11T10:43:51.442+00:00",
    },
    {
        "measurement": "measurement_name",
        "tags": {"dev-id": "device_id"},
        "fields": {"co2": 495, "rh": 42, "temp": 27.0},
        "time": "2023-07-11T10:53:51.456+00:00",
    },
]

"""


def parsed_data_to_influxdb_format(
    measurement_name, device_id, data: dict, extra_fields: dict = None, extra_tags: dict = None
) -> list:
    """
    Convert parsed data to InfluxDB datapoints format, see example above.
    :param measurement_name: name of the measurement, e.g. "elsys"
    :param device_id: device ID, e.g. "B81758FFFE031234"
    :param data: parsed data in "well-known" "JSON timeseries"-like format
    :param extra_fields: extra fields to add to each datapoint, e.g. {"rssi": rssi_value}
    :param extra_tags: extra tags to add to each datapoint, e.g. {"dev-type": "sensor"}
    """
    influxdb_points = []
    columns = data["header"]["columns"]
    parsed_data = data["data"]

    for entry in parsed_data:
        fields = extra_fields.copy() if extra_fields else {}
        for column, value in entry["f"].items():
            field_name = columns[column]["name"]
            field_value = value["v"]
            fields[field_name] = field_value

        influxdb_point = {
            "measurement": measurement_name,
            "tags": {"dev-id": device_id} | (extra_tags or {}),  # merge dicts
            "fields": fields,
            "time": entry["time"],
        }
        influxdb_points.append(influxdb_point)

    return influxdb_points


def main():
    init_script()
    url, token, org, bucket = get_influxdb_args()
    client = create_influxdb_client(url, token, org)
    parsed_data_topic = os.getenv("KAFKA_PARSED_DATA_TOPIC_NAME")
    logging.info(f"Get Kafka consumer for {parsed_data_topic}")
    # Create Kafka consumer for incoming parsed data messages
    consumer = get_kafka_consumer_by_envs(parsed_data_topic)
    if consumer is None:
        logging.critical("Kafka connection failed, exiting.")
        exit(1)

    # Loop forever for incoming messages
    logging.info("Persister is waiting for raw data messages from Kafka.")
    for msg in consumer:
        logging.info("Preparing to save data")
        data = data_unpack(msg.value)
        logging.debug(pformat(data, width=120))
        measurement_name = data["device"]["parser_module"].split(".")[-1]
        device_id = data["device"]["device_id"]
        influxdb_datapoints = parsed_data_to_influxdb_format(measurement_name, device_id, data)
        with client.write_api(write_options=SYNCHRONOUS) as write_api:
            write_api.write(bucket, org, influxdb_datapoints)
            logging.info(f"Saved {len(influxdb_datapoints)} datapoints to InfluxDB")
            logging.debug(pformat(influxdb_datapoints, width=120))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Bye!")
