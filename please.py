import logging
import argparse
from utils.config_loader import load_config
from modules.aws_module import (
    verify_aws_connection,
    list_active_accounts,
    # get_alternate_contacts,
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

def get_alternate_contacts_for_all_accounts(config):
    """
    Retrieve alternate contacts for all active accounts in AWS Organizations.
    """
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info(f"Found {len(accounts)} active accounts. Querying alternate contacts...")
    for account in accounts:
        contacts = get_alternate_contacts(
            account_id=account["Id"],
            region=config["aws"]["default_region"],
        )
        if "Error" in contacts:
            logger.error(f"Failed to retrieve contacts for account {account['Id']}: {contacts['Error']}")
        else:
            logger.info(f"Alternate Contacts for Account {account['Id']}:")
            logger.info(f"  Billing Contact: {contacts['BillingContact']}")
            logger.info(f"  Operations Contact: {contacts['OperationsContact']}")
            logger.info(f"  Security Contact: {contacts['SecurityContact']}")

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
    args = parser.parse_args()

    # Load configuration
    config = load_config()

    if args.connection:
        test_connections(config)
    elif args.list_accounts:
        list_accounts(config)
    # elif args.get_alternate_contacts:
    #     get_alternate_contacts_for_all_accounts(config)
    else:
        logger.info("No action specified. Use --help to see available options.")

if __name__ == "__main__":
    main()
