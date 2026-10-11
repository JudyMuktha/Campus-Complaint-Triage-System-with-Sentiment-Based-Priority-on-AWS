import json
import os
import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

REGION = os.environ.get("AWS_REGION", "ap-south-1")
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(os.environ.get("TABLE_NAME", "Complaints"))
comprehend = boto3.client("comprehend", region_name=REGION)
sns = boto3.client("sns", region_name=REGION)

# One SNS topic per department (set as Lambda environment variables)
TOPIC_ARNS = {
    "HOSTEL": os.environ.get("HOSTEL_TOPIC_ARN"),
    "ACADEMIC": os.environ.get("ACADEMIC_TOPIC_ARN"),
    "TRANSPORT": os.environ.get("TRANSPORT_TOPIC_ARN"),
    "ADMIN": os.environ.get("ADMIN_TOPIC_ARN"),
}

CATEGORY_KEYWORDS = {
    "HOSTEL": ["hostel", "mess", "warden", "room", "water", "laundry"],
    "ACADEMIC": ["lab", "class", "faculty", "exam", "projector", "wifi"],
    "TRANSPORT": ["bus", "driver", "route", "transport", "van"],
}

URGENT_KEYWORDS = ["urgent", "emergency", "fire", "injur", "sick", "unsafe",
                   "harass", "ragging", "short circuit", "no water", "medical"]


def classify_department(text):
    """Keyword-count classifier: returns the best matching department."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    scores = {d: len(words & set(k)) for d, k in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "ADMIN"


def compute_priority(sentiment_scores, text):
    """Rule-based priority score (0-100) from sentiment and urgent words."""
    score = sentiment_scores["Negative"] * 60 + sentiment_scores["Mixed"] * 20
    urgent_hits = [k for k in URGENT_KEYWORDS if k in text.lower()]
    if urgent_hits:
        score += 40
    score = min(int(round(score)), 100)
    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"
    return level, score, urgent_hits


def reply(status, body):
    return {"statusCode": status, "body": json.dumps(body)}


def lambda_handler(event, context):
    try:
        # Works with API Gateway (event["body"]) or a direct test event
        payload = json.loads(event["body"]) if "body" in event else event
        student_id = payload["studentId"].strip()
        complaint = payload["complaint"].strip()
        if not complaint:
            return reply(400, {"message": "Complaint text is empty."})

        text = complaint[:4500]  # Comprehend limit is 5000 bytes

        # 1. Sentiment and key phrases using Amazon Comprehend
        sentiment = comprehend.detect_sentiment(Text=text, LanguageCode="en")
        phrases = comprehend.detect_key_phrases(Text=text, LanguageCode="en")
        key_phrases = [p["Text"] for p in phrases["KeyPhrases"]
                       if p["Score"] > 0.9][:5]

        # 2. Department routing and priority
        department = classify_department(complaint)
        priority, score, urgent_hits = compute_priority(
            sentiment["SentimentScore"], complaint)

        # 3. Store the complaint in DynamoDB
        complaint_id = "CMP-" + uuid.uuid4().hex[:8].upper()
        created_at = datetime.now(timezone.utc).isoformat()
        table.put_item(Item={
            "complaintId": complaint_id,
            "createdAt": created_at,
            "studentId": student_id,
            "department": department,
            "complaint": complaint,
            "sentiment": sentiment["Sentiment"],
            "negativeScore": Decimal(str(round(
                sentiment["SentimentScore"]["Negative"], 4))),
            "keyPhrases": key_phrases,
            "priority": priority,
            "priorityScore": score,
            "status": "OPEN",
        })

        # 4. Notify the responsible department through its SNS topic
        topic_arn = TOPIC_ARNS.get(department)
        if topic_arn:
            message = (
                f"Complaint ID : {complaint_id}\n"
                f"Priority     : {priority} (score {score})\n"
                f"Department   : {department}\n"
                f"Student ID   : {student_id}\n"
                f"Key phrases  : {', '.join(key_phrases)}\n"
                f"Complaint    : {complaint}"
            )
            sns.publish(
                TopicArn=topic_arn,
                Subject=f"[{priority}] New {department} complaint {complaint_id}",
                Message=message,
                MessageAttributes={"priority": {
                    "DataType": "String", "StringValue": priority}},
            )

        return reply(200, {
            "complaintId": complaint_id,
            "department": department,
            "sentiment": sentiment["Sentiment"],
            "priority": priority,
            "message": "Complaint recorded and department notified.",
        })

    except KeyError as err:
        print("Missing field:", err)
        return reply(400, {"message": "studentId and complaint are required."})
    except Exception as err:
        print("Error:", err)
        return reply(500, {"message": "Error processing complaint."})
