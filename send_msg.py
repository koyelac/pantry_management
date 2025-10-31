import os
from twilio.rest import Client
import logging
from dotenv import load_dotenv

load_dotenv()
account_sid = os.getenv("TWILIO_SID")
auth_token = os.getenv("TWILIO_TOKEN")
twilio_number = os.getenv("TWILIO_NUMBER")
to_number = os.getenv("TO_NUMBER")
logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)
client = Client(account_sid, auth_token)

		
def send_message(body_text):
    try:
        msg = client.messages.create(
            from_ = f"whatsapp:{twilio_number}",
            body = body_text,
            to = f"whatsapp:{to_number}"
            )
        logger.info(f"Message sent to {to_number} : {msg.body}")
    except Exception as e:
        logger.error(f"Error sending message to {to_number} for the error {e}")
        
