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

def get_s3_bucket_region(account_id, bucket_name):
    """
    Retrieves the AWS region for a specified S3 bucket.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        bucket_name (str): The name of the S3 bucket.

    Returns:
        str: The AWS region where the bucket resides, or an error message if the region cannot be determined.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id)
        client = session.client("s3")

        # Get the bucket location
        location = client.get_bucket_location(Bucket=bucket_name).get("LocationConstraint")
        # Handle default region for buckets with no location constraint
        if location is None:
            return "us-east-1"
        return location
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Failed to retrieve region for bucket '{bucket_name}' in account {account_id}: {error_code}")
        return f"Error: {error_code}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving the region for bucket '{bucket_name}': {e}")
        return f"Error: {str(e)}"

def get_s3_bucket_names(account_id, region):
    """
    Retrieves the names of all S3 buckets in an AWS account.
    
    Args:
        account_id (str): The AWS account ID to use as the profile name.
        region (str): The AWS region to use.
        
    Returns:
        list: A list of bucket names.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id, region_name=region)
        client = session.client("s3")
        
        # Get bucket names
        response = client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
        return bucket_names
    except ClientError as e:
        logger.error(f"Failed to retrieve S3 bucket names for account {account_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving S3 bucket names for account {account_id}: {e}")
        return []

def check_s3_bucket(account_id, region, bucket_name):
    """
    Checks for the existence of an S3 bucket.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        region (str): The AWS region.
        bucket_name (str): The name of the S3 bucket to check.

    Returns:
        bool: True if the bucket exists, False otherwise.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id, region_name=region)
        client = session.client("s3")

        # Check bucket existence
        client.head_bucket(Bucket=bucket_name)
        logger.debug(f"Bucket '{bucket_name}' exists in account {account_id}.")
        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            logger.debug(f"Bucket '{bucket_name}' does not exist in account {account_id}.")
            return False
        else:
            logger.error(f"Error checking bucket '{bucket_name}' in account {account_id}: {e}")
            return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking bucket '{bucket_name}' in account {account_id}: {e}")
        return False

def get_s3_access_logging(account_id, bucket_name):
    """
    Checks the access logging configuration for an S3 bucket.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        bucket_name (str): The name of the S3 bucket to query.

    Returns:
        str: A message indicating whether access logging is configured or the destination bucket if it is.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id)
        client = session.client("s3")

        # Get the bucket location
        bucket_region = client.get_bucket_location(Bucket=bucket_name).get("LocationConstraint", "us-east-1")
        if bucket_region is None:
            bucket_region = "us-east-1"  # Default for no location constraint

        # Initialize client for the bucket's region
        regional_client = boto3.Session(profile_name=account_id, region_name=bucket_region).client("s3")

        # Get bucket logging configuration
        logging_config = regional_client.get_bucket_logging(Bucket=bucket_name)
        if "LoggingEnabled" in logging_config:
            target_bucket = logging_config["LoggingEnabled"]["TargetBucket"]
            logger.debug(f"Access logging is configured for bucket '{bucket_name}' with target bucket '{target_bucket}'.")
            return f"Access logging configured. Destination bucket: {target_bucket}"
        else:
            logger.debug(f"Access logging is not configured for bucket '{bucket_name}'.")
            return "Access Logging Not Configured"
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Failed to retrieve access logging settings for bucket '{bucket_name}' in account {account_id}: {error_code}")
        return f"Error: {error_code}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking access logging for bucket '{bucket_name}': {e}")
        return f"Error: {str(e)}"

def set_s3_access_logging(account_id, bucket_name, access_logging_bucket):
    """
    Configures access logging for an S3 bucket.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        bucket_name (str): The name of the S3 bucket to configure logging for.
        access_logging_bucket (str): The access logging target bucket.

    Returns:
        str: A message indicating whether logging was configured successfully or if there were errors.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id)
        client = session.client("s3")

        # Get the bucket region
        bucket_region = get_s3_bucket_region(account_id, bucket_name)
        if bucket_region.startswith("Error"):
            return f"Error: Unable to determine region for bucket {bucket_name}. {bucket_region}"

        # Configure access logging
        client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": access_logging_bucket,
                    "TargetPrefix": "",
                    "TargetObjectKeyFormat": {
                        "PartitionedPrefix": {
                            "PartitionDateSource": "EventTime",
                        }
                    },
                }
            }
        )
        logger.debug(f"Access logging enabled for bucket '{bucket_name}' with target bucket '{access_logging_bucket}'.")
        return f"Access logging configured for bucket '{bucket_name}'. Logs will be stored in '{access_logging_bucket}'."
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"\t\t\tFailed to configure access logging for bucket '{bucket_name}' in account {account_id}: {access_logging_bucket} : {error_code}")
        return f"Error: {error_code}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while configuring access logging for bucket '{bucket_name}': {e}")
        return f"Error: {str(e)}"

def get_s3_bucket_notifications(account_id, bucket_name, security_event_collection_prefix):
    """
    Checks the notification configuration for an S3 bucket.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        bucket_name (str): The name of the S3 bucket to check.

    Returns:
        str: A message indicating whether notifications are enabled or not.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id)
        client = session.client("s3")

        # Get the bucket notification configuration
        notification_config = client.get_bucket_notification_configuration(Bucket=bucket_name)

        # Check if any notification configuration exists
        if notification_config.get("TopicConfigurations") or \
           notification_config.get("QueueConfigurations") or \
           notification_config.get("LambdaFunctionConfigurations"):
            logger.info(f"\tNotifications are enabled for bucket '{bucket_name}'.")
            return "Notifications enabled"
        else:
            logger.info(f"\t ~ No notifications are configured for bucket '{bucket_name}', Enabling.")
            # enable notifications via set_s3_bucket_notifications
            set_s3_bucket_notifications(account_id, bucket_name, security_event_collection_prefix)

            return "Notifications Not Enabled"
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Failed to retrieve notifications for bucket '{bucket_name}' in account {account_id}: {error_code}")
        return f"Error: {error_code}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while retrieving notifications for bucket '{bucket_name}': {e}")
        return f"Error: {str(e)}"

def set_s3_bucket_notifications(account_id, bucket_name, security_event_collection_prefix):
    """
    Configures a notification policy for an S3 bucket.

    Args:
        account_id (str): The AWS account ID to use as the profile name.
        bucket_name (str): The name of the S3 bucket to configure notifications for.
        security_event_collection_prefix (str): The prefix used to construct the target SQS queue name.

    Returns:
        str: A message indicating whether the notification policy was applied successfully or if there were errors.
    """
    try:
        # Initialize session and client
        session = boto3.Session(profile_name=account_id)
        client = session.client("s3")

        # Get the bucket region
        bucket_region = get_s3_bucket_region(account_id, bucket_name)
        if bucket_region.startswith("Error"):
            return f"Error: Unable to determine region for bucket {bucket_name}. {bucket_region}"

        # Construct the target SQS queue ARN
        queue_name = f"{security_event_collection_prefix}-{account_id}-{bucket_region}"
        queue_arn = f"arn:aws:sqs:{bucket_region}:{account_id}:{queue_name}"

        # Apply the notification policy
        client.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration={
                "QueueConfigurations": [
                    {
                        "QueueArn": queue_arn,
                        "Events": [
                            "s3:ReducedRedundancyLostObject",
                            "s3:Replication:OperationFailedReplication"
                        ],
                        "Filter": {
                            "Key": {
                                "FilterRules": [
                                    {"Name": "prefix", "Value": ""},
                                    {"Name": "suffix", "Value": ""},
                                ]
                            }
                        },
                    }
                ]
            },
        )
        logger.info(f"\t +++ Notification policy applied to bucket '{bucket_name}' with queue ARN '{queue_arn}'.")
        return f"Notification policy configured for bucket '{bucket_name}'. Target queue ARN: {queue_arn}."
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(f"Failed to apply notification policy for bucket '{bucket_name}' in account {account_id}: {error_code}")
        return f"Error: {error_code}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while applying notification policy for bucket '{bucket_name}': {e}")
        return f"Error: {str(e)}"
