import requests
import json
import time
from datetime import datetime
import pytz
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Telegram bot settings
TELEGRAM_TOKEN = '<TELEGRAM_TOKEN>'
CHAT_ID = 'chat_id>'

# URL for sending messages to Telegram
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Your API endpoint to fetch data
API_URL = "https://beta.orchestrator.nexus.xyz/users/<wallet_address>"

# Function to send message to Telegram
def send_telegram_message(message):
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    response = requests.post(TELEGRAM_API_URL, data=payload)
    if response.status_code == 200:
        logging.info("Message sent to Telegram successfully.")
    else:
        logging.error(f"Failed to send message to Telegram. Status code: {response.status_code}")

# Function to format the lastUpdated timestamp to a simpler format in Jakarta Time (WIB)
def format_last_updated(last_updated):
    # Convert timestamp to datetime object in UTC
    utc_time = datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Set timezone to Jakarta (WIB, UTC+7)
    jakarta_tz = pytz.timezone('Asia/Jakarta')
    utc_time = pytz.utc.localize(utc_time)  # Localize to UTC first
    jakarta_time = utc_time.astimezone(jakarta_tz)  # Convert to Jakarta time
    
    # Format it to a simpler string (e.g., '2025-02-21 10:10:06')
    return jakarta_time.strftime("%Y-%m-%d %H:%M:%S")

# Function to fetch data with retry mechanism
def fetch_data_with_retry():
    max_retries = 5  # Maximum number of retries
    attempt = 0

    while attempt < max_retries:
        try:
            logging.info(f"Attempting to fetch data... (Attempt {attempt + 1})")
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
            data = response.json()
            logging.info("Data fetched successfully.")
            return data
        except (requests.exceptions.RequestException, ValueError) as e:
            attempt += 1
            logging.error(f"Attempt {attempt} failed: {e}")
            time.sleep(5)  # Wait for 5 seconds before retrying
    logging.error("All attempts failed. Could not fetch data.")
    return None  # Return None if all attempts fail

# Function to fetch and send node data
def fetch_and_send_data():
    data = fetch_data_with_retry()

    if data is None:
        send_telegram_message("Failed to fetch data after multiple attempts.")
        return

    # Get the wallet address
    wallet_address = data['data']['walletAddress']

    # Extract nodes with nodeType 2 and points > 0
    nodes_with_points_type2 = [
        node for node in data['data']['nodes'] if node['nodeType'] == 2 and node['testnet_two_points'] > 0
    ]

    # Format the message with wallet address, Node ID, Points, and lastUpdated time
    message = f"Wallet Address: {wallet_address}\n\nNodes CLI Points:\n\n"
    for node in nodes_with_points_type2:
        last_updated = format_last_updated(node['lastUpdated'])  # Format the lastUpdated time to WIB
        message += f"Node ID: {node['id']} | Points: {node['testnet_two_points']} | Last Updated: {last_updated}\n\n"

    # Send the filtered data to Telegram
    if nodes_with_points_type2:
        logging.info(f"Sending the following data to Telegram:\n{message}")
        send_telegram_message(message)
    else:
        logging.warning(f"No nodes with nodeType 2 and points > 0 found for wallet address: {wallet_address}")
        send_telegram_message(f"Wallet Address: {wallet_address}\nNo nodeType 2 nodes with points > 0 found.")

# Loop with countdown (hitungan mundur)
while True:
    fetch_and_send_data()  # Call the function to get data and send to Telegram
    logging.info("Waiting for 1 hours before the next iteration.")
    
    # Wait for 10 seconds before executing again
    time.sleep(3600)  # 10 seconds
