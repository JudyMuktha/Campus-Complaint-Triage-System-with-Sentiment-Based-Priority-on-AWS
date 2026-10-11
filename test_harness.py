"""Local test harness: runs lambda_function.py with simulated AWS services.
Comprehend, DynamoDB and SNS are replaced by small in-memory stubs, so the
triage logic (routing, priority scoring, storage and notification calls) is
executed for real. Results are written to run_output.json."""
import json, os, sys, types

os.environ.update({
    "AWS_REGION": "ap-south-1", "TABLE_NAME": "Complaints",
    "HOSTEL_TOPIC_ARN": "arn:aws:sns:ap-south-1:123456789012:CCTS-Hostel",
    "ACADEMIC_TOPIC_ARN": "arn:aws:sns:ap-south-1:123456789012:CCTS-Academic",
    "TRANSPORT_TOPIC_ARN": "arn:aws:sns:ap-south-1:123456789012:CCTS-Transport",
    "ADMIN_TOPIC_ARN": "arn:aws:sns:ap-south-1:123456789012:CCTS-Admin",
})

NEG = ["no water", "sick", "late", "not working", "harass", "unsafe", "slow",
       "does not", "fear", "dirty", "broken", "urgent", "days"]
PHRASES = ["water supply", "hostel block B", "three days", "college bus", "route 12",
           "usual stop", "projector", "lab 3", "senior student", "juniors", "library", "wifi"]

class FakeComprehend:
    def detect_sentiment(self, Text, LanguageCode):
        t = Text.lower(); n = sum(1 for w in NEG if w in t)
        pos = 0.25 if "thank" in t else 0.02
        neg = min(0.97, 0.20 + 0.15 * n) if n else 0.05
        mixed = 0.35 if "thank" in t and n else 0.01
        neu = max(0.0, round(1 - neg - pos - mixed, 4))
        scores = {"Positive": pos, "Negative": neg, "Neutral": neu, "Mixed": mixed}
        label = max(scores, key=scores.get).upper()
        return {"Sentiment": label, "SentimentScore": scores}
    def detect_key_phrases(self, Text, LanguageCode):
        return {"KeyPhrases": [{"Text": p, "Score": 0.98} for p in PHRASES if p.lower() in Text.lower()]}

class FakeTable:
    def __init__(self): self.items = []
    def put_item(self, Item): self.items.append(Item)

class FakeSNS:
    def __init__(self): self.sent = []
    def publish(self, **kw): self.sent.append(kw)

table, sns = FakeTable(), FakeSNS()
sys.modules["boto3"] = types.SimpleNamespace(
    resource=lambda *a, **k: types.SimpleNamespace(Table=lambda n: table),
    client=lambda name, **k: FakeComprehend() if name == "comprehend" else sns)

import lambda_function as lf

CASES = [
    "There has been no water supply in hostel block B for three days and students are falling sick. This is very urgent.",
    "A senior student is harassing juniors near the library and we feel unsafe.",
    "The college bus on route 12 is late every morning, the driver does not stop at the usual stop, and the seats are broken and dirty.",
    "The projector in lab 3 is not working properly.",
]
out = []
for i, text in enumerate(CASES):
    event = {"studentId": "25IT1182", "complaint": text}
    resp = lf.lambda_handler(event, None)
    out.append({"event": event, "response": resp, "item": json.loads(json.dumps(table.items[-1], default=str)),
                "sns": sns.sent[-1]})
json.dump(out, open("run_output.json", "w"), indent=2)
for o in out:
    r = json.loads(o["response"]["body"])
    print(o["response"]["statusCode"], r["complaintId"], r["department"], r["sentiment"], r["priority"])
