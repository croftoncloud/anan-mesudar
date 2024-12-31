import logging
import argparse
from utils.config_loader import load_config
from modules.aws_module import (
    verify_aws_connection,
    list_active_accounts,
    get_alternate_contacts,
    set_alternate_contacts,
)
from modules.jira_module import verify_jira_connection
from modules.slack_module import verify_slack_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    # format="%(asctime)s - %(levelname)s - %(message)s",
    format="%(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("botocore").setLevel(logging.WARNING)

def test_connections(config):
    """Run connection tests for AWS, Jira, and Slack."""
    logger.info("Testing AWS Management Account connection...")
    verify_aws_connection(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info("Testing AWS Audit Account connection...")
    verify_aws_connection(
        account_id=config["aws"]["audit_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info("Verifying Jira connection...")
    verify_jira_connection(
        config["jira"]["url"],
        config["jira"]["user"],
        config["jira"]["token"],
    )

    logger.info("Verifying Slack connection...")
    verify_slack_connection(config["slack"]["webhook_url"])

def list_accounts(config):
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )
    for account in accounts:
        logger.info(f"Account ID: {account['Id']}, Name: {account['Name']}, Email: {account['Email']}")

def format_contact(contact):
    """
    Format the contact information for human-readable output.

    Args:
        contact (dict): The contact information dictionary.

    Returns:
        str: Formatted string for the contact information.
    """
    if not contact:
        return "Not Set"
    return (
        f"\tName: {contact.get('Name', 'N/A')}\n"
        f"\tEmail: {contact.get('EmailAddress', 'N/A')}\n"
        f"\tPhone: {contact.get('PhoneNumber', 'N/A')}\n"
        f"\tTitle: {contact.get('Title', 'N/A')}"
    )

def get_alternate_contacts_for_all_accounts(config):
    """
    Retrieve alternate contacts for all active accounts in AWS Organizations.
    """
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info(f"Found {len(accounts)} active accounts. Querying alternate contacts...\n")
    for account in accounts:
        logger.info(f"Retrieving alternate contacts for account {account['Id']} ({account['Name']})...\n")
        contacts = get_alternate_contacts(
            account_id=account["Id"],
            region=config["aws"]["default_region"],
        )

        if "Error" in contacts:
            logger.error(f"Failed to retrieve contacts for account {account['Id']}: {contacts['Error']}")
        else:
            logger.info(
                f"Alternate Contacts for Account {account['Id']} ({account['Name']}):\n"
                f"  Billing Contact:\n{format_contact(contacts['BillingContact'])}\n"
                f"  Operations Contact:\n{format_contact(contacts['OperationsContact'])}\n"
                f"  Security Contact:\n{format_contact(contacts['SecurityContact'])}\n"
            )

def set_alternate_contacts_for_all_accounts(config):
    """
    Set alternate contacts for all active accounts in AWS Organizations.
    """
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info(f"Found {len(accounts)} active accounts. Setting alternate contacts...")
    for account in accounts:
        logger.info(f"Setting alternate contacts for account {account['Id']}...")
        success = set_alternate_contacts(
            account_id=account["Id"],
            region=config["aws"]["default_region"],
            config=config,
        )
        if success:
            logger.info(f"Successfully set alternate contacts for account {account['Id']}.")
        else:
            logger.error(f"Failed to set alternate contacts for account {account['Id']}.")

def main():
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Run connection tests or other operations.")
    parser.add_argument("--connection", action="store_true", help="Test AWS connections for all accounts.")
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List all active accounts in AWS Organizations."
    )
    parser.add_argument(
        "--get-alternate-contacts",
        action="store_true",
        help="Retrieve alternate contact information for all active accounts.",
    )
    parser.add_argument(
        "--set-alternate-contacts",
        action="store_true",
        help="Set alternate contact information."
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config()

    if args.connection:
        test_connections(config)
    elif args.list_accounts:
        list_accounts(config)
    elif args.get_alternate_contacts:
        get_alternate_contacts_for_all_accounts(config)
    elif args.set_alternate_contacts:
        set_alternate_contacts_for_all_accounts(config)
    else:
        logger.info("No action specified. Use --help to see available options.")

if __name__ == "__main__":
    main()
