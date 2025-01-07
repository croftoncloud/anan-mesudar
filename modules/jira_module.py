# modules/jira_module.py
import requests
import logging

logger = logging.getLogger(__name__)

def verify_jira_connection(url, user, token):
    '''
    Verify that the Jira connection is successful.

    Args:
        url (str): The Jira base URL.
        user (str): The Jira username.
        token (str): The Jira

    Returns:
        None
    '''
    try:
        response = requests.get(
            f"{url}/rest/api/3/myself",
            auth=(user, token),
        )
        if response.status_code == 200:
            logger.info("Jira connection verified successfully.")
        else:
            logger.error(f"Failed to connect to Jira: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Failed to connect to Jira: {e}")
