"""AWS SES email sender (Phase 0). boto3 lazy-imported. Bodies carry links only."""

from __future__ import annotations


class SesEmailSender:
    def __init__(self, region: str, from_address: str) -> None:
        import boto3

        self._from = from_address
        self._client = boto3.client("ses", region_name=region)

    def send(self, to: str, subject: str, body: str) -> None:
        self._client.send_email(
            Source=self._from,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject},
                "Body": {"Text": {"Data": body}},
            },
        )
