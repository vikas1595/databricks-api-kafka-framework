import os
import json
import time
import logging
from faker import Faker
from kafka import KafkaProducer
from dotenv import load_dotenv

# --- NEW: Load environment variables from .env file ---
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MODIFIED: Kafka configuration from environment variables ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER")
TOPIC_NAME = os.getenv("KAFKA_TOPIC")
CONNECTION_STRING = os.getenv("KAFKA_CONNECTION_STRING")

# Check if essential configuration is missing
if not all([KAFKA_BROKER, TOPIC_NAME, CONNECTION_STRING]):
    raise ValueError("Please set KAFKA_BROKER, KAFKA_TOPIC, and KAFKA_CONNECTION_STRING in your .env file.")

# Initialize Faker
fake = Faker()

def create_producer():
    """Creates a Kafka producer configured for Azure Event Hubs."""
    try:
        # --- MODIFIED: Added SASL authentication for Event Hubs ---
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            security_protocol='SASL_SSL',
            sasl_mechanism='PLAIN',
            sasl_plain_username='$ConnectionString', # This is a literal string
            sasl_plain_password=CONNECTION_STRING,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        logging.info("Kafka producer created successfully.")
        return producer
    except Exception as e:
        logging.error(f"Error creating Kafka producer: {e}")
        return None

def generate_taxi_trip_data(include_tip=False):
    """Generates a single record of fake NYC taxi trip data."""
    data = {
        "vendor_id": fake.random_element(elements=("1", "2")),
        "pickup_datetime": fake.date_time_this_year().isoformat(),
        "dropoff_datetime": fake.date_time_this_year().isoformat(),
        "passenger_count": fake.random_int(min=1, max=6),
        "trip_distance": round(fake.random_number(digits=2, fix_len=False), 2),
        "rate_code_id": fake.random_int(min=1, max=6),
        "payment_type": fake.random_int(min=1, max=4),
        "fare_amount": round(fake.random_number(digits=2, fix_len=False), 2)
    }
    if include_tip:
        data["tip_amount"] = round(fake.random_number(digits=2, fix_len=False), 2)
    return data

def main():
    """Main function to generate and send data to Kafka."""
    producer = create_producer()
    if not producer:
        return

    logging.info(f"Sending messages to topic: {TOPIC_NAME}")

    # Send initial messages without tip_amount
    for i in range(15):
        message = generate_taxi_trip_data(include_tip=False)
        producer.send(TOPIC_NAME, value=message)
        logging.info(f"Sent message {i+1}/30 (initial schema)")
        time.sleep(1)

    # Simulate schema drift by adding tip_amount
    for i in range(15):
        message = generate_taxi_trip_data(include_tip=True)
        producer.send(TOPIC_NAME, value=message)
        logging.info(f"Sent message {i+16}/30 (with tip_amount)")
        time.sleep(1)

    producer.flush()
    producer.close()
    logging.info("Finished sending messages.")

if __name__ == "__main__":
    main()