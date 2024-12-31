# modules/aws_module.py
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import logging

logger = logging.getLogger(__name__)

def verify_aws_connection(account_id, region):
    try:
        session = boto3.Session(profile_name=account_id, region_name=region)
        client = session.client("sts")
        caller_identity = client.get_caller_identity()

        if caller_identity["Account"] == account_id:
            logger.info("AWS connection verified successfully.")
            logger.info(f"Region: {session.region_name}")
            logger.info(f"Account ID: {caller_identity['Account']}")
            logger.info(f"User ARN: {caller_identity['Arn']}")
        else:
            logger.warning("Connected to a different account than expected.")
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"Failed to connect to AWS: {e}")
    except Exception as e:
        logger.error(f"An error occurred while connecting to AWS: {e}")


def list_active_accounts(account_id, region):
    """
    Retrieves all active accounts in an AWS Organization.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        region (str): The AWS region to use.

    Returns:
        list: A list of dictionaries containing active account details.
    """
    try:
        session = boto3.Session(profile_name=account_id, region_name=region)
        client = session.client("organizations")

        accounts = []
        paginator = client.get_paginator("list_accounts")
        for page in paginator.paginate():
            for account in page["Accounts"]:
                if account["Status"] == "ACTIVE":
                    accounts.append(account)

        logger.info(f"Retrieved {len(accounts)} active accounts from AWS Organizations.")
        return accounts
    except client.exceptions.AWSOrganizationsNotInUseException as e:
        logger.error("The AWS Organizations service is not available in this account.")
        return []
    except Exception as e:
        logger.error(f"An error occurred while retrieving active accounts: {e}")
        return []

def get_alternate_contacts(account_id, region):
    """
    Retrieves alternate contact information for a given AWS account.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        region (str): The AWS region to use.

    Returns:
        dict: A dictionary containing alternate contact information.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id, region_name=region)
        client = session.client("account")

        # Retrieve alternate contacts
        def fetch_contact(contact_type):
            try:
                return client.get_alternate_contact(AlternateContactType=contact_type).get("AlternateContact", {})
            except client.exceptions.ResourceNotFoundException:
                logger.info(f"No {contact_type.lower()} contact set for account {account_id}.")
                return None

        billing_contact = fetch_contact("BILLING")
        operations_contact = fetch_contact("OPERATIONS")
        security_contact = fetch_contact("SECURITY")

        return {
            "AccountID": account_id,
            "BillingContact": billing_contact,
            "OperationsContact": operations_contact,
            "SecurityContact": security_contact,
        }
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "AccessDeniedException":
            logger.error(f"Access denied while retrieving contacts for account {account_id}.")
            return {"AccountID": account_id, "Error": "AccessDenied"}
        else:
            logger.error(f"ClientError while retrieving contacts for account {account_id}: {e}")
            return {"AccountID": account_id, "Error": error_code}
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving contacts for account {account_id}: {e}")
        return {"AccountID": account_id, "Error": str(e)}

def set_alternate_contacts(account_id, region, config):
    """
    Sets alternate contact information for a given AWS account.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        region (str): The AWS region to use.
        config (dict): Configuration dictionary containing alternate contact details.

    Returns:
        bool: True if all contacts were set successfully, False otherwise.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id, region_name=region)
        client = session.client("account")

        # Helper function to set a single contact type
        def set_contact(contact_type, name, email, phone, title):
            client.put_alternate_contact(
                AlternateContactType=contact_type,
                Name=name,
                EmailAddress=email,
                PhoneNumber=phone,
                Title=title,
            )
            logger.info(f"Successfully set {contact_type.lower()} contact for account {account_id}.")

        # Set billing contact
        set_contact(
            "BILLING",
            config["aws"]["alternate_contact_billing_name"],
            config["aws"]["alternate_contact_billing_email"],
            config["aws"]["alternate_contact_billing_phone"],
            config["aws"]["alternate_contact_billing_title"],
        )

        # Set operations contact
        set_contact(
            "OPERATIONS",
            config["aws"]["alternate_contact_operations_name"],
            config["aws"]["alternate_contact_operations_email"],
            config["aws"]["alternate_contact_operations_phone"],
            config["aws"]["alternate_contact_operations_title"],
        )

        # Set security contact
        set_contact(
            "SECURITY",
            config["aws"]["alternate_contact_security_name"],
            config["aws"]["alternate_contact_security_email"],
            config["aws"]["alternate_contact_security_phone"],
            config["aws"]["alternate_contact_security_title"],
        )

        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Failed to set alternate contacts for account {account_id}: {error_code}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while setting alternate contacts for account {account_id}: {e}")
        return False
