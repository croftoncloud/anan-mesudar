'''
Clear Guard Duty findings for a fresh start.
utils/clear_guard_duty_findings.py
'''
import argparse
import sys
import logging
import boto3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Adjust logging for boto3 and botocore
logging.getLogger("botocore").setLevel(logging.WARNING)

def get_enabled_regions(account_id, aws_default_region):
    """
    Retrieve all enabled regions in the specified AWS account.

    Args:
        account_id (str): AWS account ID.
        aws_default_region (str): Default AWS region.

    Returns:
        list: List of enabled regions in the account.
    """
    try:
        session = boto3.Session(profile_name=account_id, region_name=aws_default_region)
        ec2_client = session.client("ec2")
        regions = ec2_client.describe_regions(AllRegions=True)["Regions"]
        enabled_regions = [
            region["RegionName"]
            for region in regions
            if region["OptInStatus"] in ["opt-in-not-required", "opted-in"]
        ]
        return enabled_regions
    except boto3.exceptions.Boto3Error as boto_err:
        logger.error("Boto3 error fetching enabled regions: %s", boto_err)
        sys.exit(1)

def archive_guardduty_findings(account_id, region):
    """
    Archive all GuardDuty findings in the specified region.

    Args:
        account_id (str): AWS account ID.
        region (str): AWS region name.

    Returns:
        None
    """
    try:
        session = boto3.Session(profile_name=account_id, region_name=region)
        gd_client = session.client("guardduty")

        detectors = gd_client.list_detectors()["DetectorIds"]

        if not detectors:
            logger.info("No GuardDuty detectors found in region %s.", region)
            return

        for detector_id in detectors:
            next_token = None
            while True:
                try:
                    params = {"DetectorId": detector_id}
                    if next_token:
                        params["NextToken"] = next_token

                    findings_response = gd_client.list_findings(**params)
                    findings = findings_response.get("FindingIds", [])

                    if findings:
                        gd_client.archive_findings(DetectorId=detector_id, FindingIds=findings)
                        logger.info("Archived %s findings in region %s for detector %s.", len(findings), region, detector_id)
                    else:
                        logger.info("No findings to archive in region %s for detector %s.", region, detector_id)

                    next_token = findings_response.get("NextToken")
                    if not next_token:
                        break
                except boto3.exceptions.Boto3Error as boto_err:
                    logger.error("Boto3 error processing findings for detector %s in region %s: %s", detector_id, region, boto_err)
    except boto3.exceptions.Boto3Error as boto_err:
        logger.error("Boto3 error initializing GuardDuty client in region %s: %s", region, boto_err)

def main():
    """
    Main function to archive GuardDuty findings across all enabled regions in the account.
    """
    parser = argparse.ArgumentParser(description="Archive GuardDuty findings across all enabled regions.")
    parser.add_argument("--account", required=True, help="AWS account ID.")
    parser.add_argument("--region", required=False, help="AWS region to start with.")

    args = parser.parse_args()
    aws_account_id = args.account
    aws_region = args.region
    aws_default_region = "us-east-1"

    # Get all enabled regions in the account
    if aws_region:
        logger.info("Region was specified. Processing only the specified region: %s", aws_region)
        enabled_regions = [aws_region]
    else:
        logger.info("Region was not specified. Processing all enabled regions.")
        enabled_regions = get_enabled_regions(aws_account_id, aws_default_region)

    # Iterate through each enabled region to archive GuardDuty findings
    for region in enabled_regions:
        logger.info("Processing: %s %s", aws_account_id, region)
        archive_guardduty_findings(aws_account_id, region)

    logger.info("GuardDuty findings archiving completed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
