# anan-mesudar: cloud organized

This project is meant to help create and maintain a NIST 800-53 compliant AWS environment. It will include:

- Templates (CloudFormation, Terraform) to build secure reference architecture
- Scripts (Python, bash) to assess current settings and determine corrective actions
- Ticket Integration to ensure all security defects are ticketed for engineering teams
- Reporting on environmental health and defect turnover
- Documentation examples demonstrating how to create actionable content for cloud teams

## Assumptions

What assumptions are held before using this framework?

Examples:

- AWS Organizations is enabled
- Control Tower is enabled and configured with an Audit account
- You read these scripts and templates before deploying them

## Repository Organization

This organization is subject to change, but initially there will be:

```
.
├── config.yaml
├── modules
│   ├── aws_module.py
│   ├── __init__.py
│   ├── jira_module.py
│   └── slack_module.py
├── please.py
├── README.md
└── utils
    ├── config_loader.py
    ├── __init__.py
```
