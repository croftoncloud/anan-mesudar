'''
CLI script to perform various operations on AWS, Jira, and Slack.
'''
import logging
import argparse
from utils.config_loader import load_config
from modules.aws_module import (
    verify_aws_connection,
    list_active_accounts,
    get_alternate_contacts,
    set_alternate_contacts,
    get_s3_bucket_names,
    check_s3_bucket,
    get_s3_access_logging,
    get_s3_bucket_region,
    set_s3_access_logging,
    get_s3_bucket_notifications,
    set_s3_bucket_notifications,
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
    """
    Run connection tests for AWS, Jira, and Slack.

    Args:
        config (dict): The loaded configuration file.

    Returns:
        None

    Raises:
        Exception: If any of the connection tests fail.

    """
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
    """
    List all active accounts in AWS Organizations.

    Args:
        config (dict): The loaded configuration file.

    Returns:
        accounts (list): List of active accounts in AWS Organizations.
    """
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

    Args:
        config (dict): The loaded configuration file.

    Returns:
        None    
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

    Args:
        config (dict): The loaded configuration file.

    Returns:
        None
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

def check_s3_buckets_for_all_accounts(config):
    """
    Check for the existence of S3 buckets for all active accounts in AWS Organizations.
    """
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info(f"Found {len(accounts)} active accounts. Checking S3 buckets...\n")
    prefix = config["aws"]["security_event_collection_prefix"]
    for account in accounts:
        bucket_name = f"{prefix}-{account['Id']}-{config['aws']['default_region']}"
        logger.info(f"Checking bucket '{bucket_name}' for account {account['Id']} ({account['Name']})...\n")
        exists = check_s3_bucket(
            account_id=account["Id"],
            region=config["aws"]["default_region"],
            bucket_name=bucket_name,
        )
        if exists:
            logger.info(f"Bucket '{bucket_name}' exists in account {account['Id']}.")
        else:
            logger.info(f"Bucket '{bucket_name}' does not exist in account {account['Id']}.")

def get_access_logging_for_all_buckets(config):
    """
    Query access logging settings for S3 buckets in all active accounts.

    Args:
        config (dict): The loaded configuration file.
    """
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info(f"Found {len(accounts)} active accounts. Checking S3 buckets for access logging...")
    prefix = config["aws"]["security_event_collection_prefix"]
    for account in accounts:

        buckets=get_s3_bucket_names(
            account_id=account["Id"],
            region=config["aws"]["default_region"],
        )
        logger.info(f"Found {len(buckets)} buckets in account {account['Id']} ({account['Name']}).")

        for bucket in buckets:
            # get the bucket region to build the access logging name correctly
            bucket_region = get_s3_bucket_region(
                account_id=account["Id"],
                bucket_name=bucket,
            )
            # Access logging bucket name
            access_logging_bucket_name = f"{prefix}-{account['Id']}-{bucket_region}"
            # if the bucket name matches the controltower_s3_access_logs from config.yaml, skip it
            # if the bucket being reviewed matches bucket_name, print a comment and skip it.
            if bucket == config["aws"]["controltower_s3_access_logs"]:
                logger.info(f"\t ~ Skipping bucket '{bucket}' in account {account['Id']} ({account['Name']})...")
            elif bucket == access_logging_bucket_name:
                logger.info(f"\t ~ Skipping bucket '{bucket}' in account {account['Id']} ({account['Name']})...")
            else:
                result = get_s3_access_logging(
                    account_id=account["Id"],
                    bucket_name=bucket,
                )
                # logger.info(f"\tAccess Logging for Bucket '{bucket}': {result}")
                # if result is "Access Logging Not Configured" the print a warning message
                if result == "Access Logging Not Configured":
                    logger.warning(f"\t --> Access Logging is not configured for bucket '{bucket}' in account {account['Id']} ({account['Name']}).")
                    # Set access logging for the bucket
                    set_result = set_s3_access_logging(
                        account_id=account["Id"],
                        bucket_name=bucket,
                        access_logging_bucket=access_logging_bucket_name,
                    )
                    if set_result:
                        # if the result is an error, print an error message
                        if "Error" in set_result:
                            logger.error(f"\t xxxxx--> Failed to configure Access Logging for bucket '{bucket}' in account {account['Id']} ({account['Name']}).")
                        else:
                            logger.info(f"\t --+++--> Access Logging has been configured for bucket '{bucket}' in account {account['Id']} ({account['Name']}).")
                    else:
                        logger.error(f"\t xxxxx--> Failed to configure Access Logging for bucket '{bucket}' in account {account['Id']} ({account['Name']}).")
                else:
                    logger.info(f"\tAccess Logging for Bucket '{bucket}': {result}")

def get_s3_bucket_notifications_for_all_buckets(config):
    '''
    Query S3 bucket notifications for all buckets in an account.

    Args:
        account_id (str): The AWS account ID.
        bucket_name (str): The S3 bucket name.

    Returns:
        None

    '''
    logger.info("Retrieving active accounts in AWS Organizations...")
    accounts = list_active_accounts(
        account_id=config["aws"]["management_account_id"],
        region=config["aws"]["default_region"],
    )

    logger.info(f"Found {len(accounts)} active accounts. Checking S3 buckets...\n")
    for account in accounts:
        bucket_names = get_s3_bucket_names(
            account_id=account["Id"],
            region=config["aws"]["default_region"],
        )
        logger.info(f"Found {len(bucket_names)} buckets in account {account['Id']} ({account['Name']}).")
        for bucket_name in bucket_names:
            get_s3_bucket_notifications(
                account_id=account["Id"],
                bucket_name=bucket_name,
                security_event_collection_prefix=config["aws"]["security_event_collection_prefix"],
            )


def main():
    '''
    Main function to parse CLI arguments and run the appropriate action.
    '''
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Run connection tests or other operations.")
    parser.add_argument(
        "--connection",
        action="store_true",
        help="Test AWS connections for all accounts."
    )
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
    parser.add_argument(
        "--s3-check",
        action="store_true",
        help="Check for the existence of specific S3 buckets."
    )
    parser.add_argument(
        "--s3-get-access-logging",
        action="store_true",
        help="Query access logging settings for S3 buckets."
    )
    parser.add_argument(
        "--set-s3-access-logging",
        action="store_true",
        help="Enable access logging for S3 buckets."
    )
    parser.add_argument(
        "--get-s3-bucket-notifications",
        action="store_true",
        help="Query S3 bucket notifications."
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
    elif args.s3_check:
        check_s3_buckets_for_all_accounts(config)
    elif args.s3_get_access_logging:
        get_access_logging_for_all_buckets(config)
    elif args.get_s3_bucket_notifications:
        get_s3_bucket_notifications_for_all_buckets(config)
    else:
        logger.info("No action specified. Use --help to see available options.")

if __name__ == "__main__":
    main()
