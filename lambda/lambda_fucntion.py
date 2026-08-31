import base64
import json
import os
import uuid
from datetime import datetime, timezone

import boto3


dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
ses = boto3.client("ses")


table_name = os.environ["TABLE_NAME"]
document_bucket = os.environ["DOCUMENT_BUCKET"]
sender_email = os.environ["SES_SENDER"]
recipient_email = os.environ["SES_RECIPIENT"]

table = dynamodb.Table(table_name)


def lambda_handler(event, context):

    print("Received request")
    http_method = event.get("httpMethod")

    if http_method == "OPTIONS":
        return response(
            200,
            {
                "message": "CORS preflight successful"
            }
        )
    try:

        body = event.get("body")

        if isinstance(body, str):
            body = json.loads(body)

        if not body:
            return response(
                400,
                {
                    "message": "Request body is required"
                }
            )

        name = body.get("name", "").strip()
        email = body.get("email", "").strip()
        message = body.get("message", "").strip()

        if not name or not email or not message:
            return response(
                400,
                {
                    "message": "name, email and message are required"
                }
            )

        feedback_id = f"fb-{uuid.uuid4().hex[:12]}"

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        file_key = None

        # Handle optional PDF upload
        file_content = body.get("fileContent")
        file_name = body.get("fileName")

        if file_content and file_name:

            if not file_name.lower().endswith(".pdf"):
                return response(
                    400,
                    {
                        "message": "Only PDF files are allowed"
                    }
                )

            try:

                decoded_file = base64.b64decode(
                    file_content
                )

            except Exception:

                return response(
                    400,
                    {
                        "message": "Invalid file encoding"
                    }
                )

            # 5 MB limit
            if len(decoded_file) > 5 * 1024 * 1024:

                return response(
                    400,
                    {
                        "message": "File size must be less than 5 MB"
                    }
                )

            year = datetime.now(
                timezone.utc
            ).strftime("%Y")

            month = datetime.now(
                timezone.utc
            ).strftime("%m")

            file_key = (
                f"uploads/{year}/{month}/"
                f"{feedback_id}.pdf"
            )

            s3.put_object(
                Bucket=document_bucket,
                Key=file_key,
                Body=decoded_file,
                ContentType="application/pdf"
            )

            print(
                f"Document uploaded: {file_key}"
            )

        item = {
            "feedbackId": feedback_id,
            "name": name,
            "email": email,
            "message": message,
            "createdAt": created_at,
            "status": "SUBMITTED"
        }

        if file_key:
            item["fileKey"] = file_key

        table.put_item(
            Item=item
        )

        try:

            send_notification(
                feedback_id,
                name,
                email,
                message
            )

        except Exception as email_error:

            print(
                f"Email notification failed: {str(email_error)}"
            )

        print(
            f"Feedback stored successfully: {feedback_id}"
        )

        return response(
            201,
            {
                "message": "Feedback submitted successfully",
                "feedbackId": feedback_id,
                "fileUploaded": bool(file_key)
            }
        )

    except Exception as error:

        print(
            f"Error processing feedback: {str(error)}"
        )

        return response(
            500,
            {
                "message": "Internal server error"
            }
        )


def response(status_code, body):

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(body)
    }

def send_notification(feedback_id, name, email, message):

    subject = f"New Feedback: {feedback_id}"

    body = f"""
New feedback has been submitted.

Feedback ID: {feedback_id}

Name: {name}

Email: {email}

Message:
{message}
"""

    ses.send_email(
        Source=sender_email,
        Destination={
            "ToAddresses": [
                recipient_email
            ]
        },
        Message={
            "Subject": {
                "Data": subject
            },
            "Body": {
                "Text": {
                    "Data": body
                }
            }
        }
    )

    print(
        f"Notification email sent for {feedback_id}"
    )