from __future__ import annotations

from typing import Any

from boto3.session import Session
from botocore.exceptions import ClientError


def get_secret(secret_name: str) -> str:
    """Get secret for website private key."""
    region_name = "us-east-2"

    # Create a Secrets Manager client
    session: Any = Session()
    client: Any = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response: dict[str, Any] = client.get_secret_value(SecretId=secret_name)
    except ClientError:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise

    secret = get_secret_value_response.get("SecretString")
    if not isinstance(secret, str):
        raise ValueError("SecretString missing from Secrets Manager response.")
    return secret
