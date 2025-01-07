# modules/slack_module.py
import requests
import logging

logger = logging.getLogger(__name__)

def verify_slack_connection(webhook_url):
    '''
    Verify that the Slack connection is successful.
    
    Args:
        webhook_url (str): The Slack webhook URL.

    Returns:
        None
    '''
    try:
        response = requests.post(
            webhook_url,
            json={"text": "Testing Slack integration."},
        )
        if response.status_code == 200:
            logger.info("Slack connection verified successfully.")
        else:
            logger.error(f"Failed to connect to Slack: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to connect to Slack: {e}")
