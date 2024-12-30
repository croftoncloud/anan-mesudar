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
        billing_contact = client.get_alternate_contact(ContactType="BILLING").get("AlternateContact", {})
        operations_contact = client.get_alternate_contact(ContactType="OPERATIONS").get("AlternateContact", {})
        security_contact = client.get_alternate_contact(ContactType="SECURITY").get("AlternateContact", {})

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