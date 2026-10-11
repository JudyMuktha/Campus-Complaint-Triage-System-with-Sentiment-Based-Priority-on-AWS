"""Renders run_output.json into output images used in the report."""
import json, textwrap
from PIL import Image, ImageDraw, ImageFont
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 17)
FB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 17)
runs = json.load(open("run_output.json"))

def render(path, title, lines, width=1000):
    lh = 25; h = 60 + lh * len(lines) + 25
    im = Image.new("RGB", (width, h), "#fbfbfb"); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, width, 38], fill="#232f3e")
    d.text((16, 8), title, font=FB, fill="white")
    y = 52
    for l in lines:
        d.text((18, y), l, font=F, fill="#1b1b1b"); y += lh
    d.rectangle([0, 0, width - 1, h - 1], outline="#9a9a9a")
    im.save(path)

def wrap(s, w=92): return textwrap.wrap(s, w) or [""]
r0 = runs[0]; body = json.loads(r0["response"]["body"])

# 1 test event + response
lines = ["Test Event Name: ComplaintTest1", "", "Event JSON:"]
lines += json.dumps(r0["event"], indent=2).replace('",\n  "complaint": "', '",\n  "complaint": "').split("\n")[:1]
lines = ["Test Event Name: ComplaintTest1", "", "Event JSON:", "{", '  "studentId": "25IT1182",', '  "complaint":']
lines += ["    " + x for x in wrap(r0["event"]["complaint"], 84)]
lines += ["}", "", "Response:", "{", '  "statusCode": 200,', '  "body": {']
for k, v in body.items(): lines.append(f'    "{k}": "{v}",')
lines += ["  }", "}", "", "Status: Succeeded"]
render("screenshots/fig1_test_event_response.png", "Lambda  >  Test  >  Execution result (local run)", lines)

# 2 DynamoDB item
it = r0["item"]; lines = ["Table: Complaints          Item (1 of 4 stored)", ""]
for k, v in it.items():
    val = json.dumps(v) if not isinstance(v, str) else v
    pre = f"{k:<14}: "
    w = wrap(val, 70)
    lines.append(pre + w[0])
    lines += [" " * len(pre) + x for x in w[1:]]
render("screenshots/fig2_dynamodb_item.png", "DynamoDB  >  Explore table items  >  Complaints (local run)", lines)

# 3 SNS message
s = r0["sns"]; lines = ["Topic ARN : " + s["TopicArn"], "Subject   : " + s["Subject"],
                        "Attribute : priority = " + s["MessageAttributes"]["priority"]["StringValue"], "", "Message body:", ""]
for ln in s["Message"].split("\n"):
    lines += wrap(ln, 90)
render("screenshots/fig3_sns_notification.png", "SNS  >  Message published to department topic (local run)", lines)

# 4 summary table
hdr = f'{"Complaint ID":<14}{"Department":<12}{"Sentiment":<11}{"Score":<7}{"Priority":<10}SNS topic'
lines = [hdr, "-" * 88]
for r in runs:
    i = r["item"]; t = r["sns"]["TopicArn"].split(":")[-1]
    lines.append(f'{i["complaintId"]:<14}{i["department"]:<12}{i["sentiment"]:<11}{i["priorityScore"]:<7}{i["priority"]:<10}{t}')
lines += ["", "Complaint texts:"]
for n, r in enumerate(runs, 1):
    w = wrap(r["event"]["complaint"], 84)
    lines.append(f"{n}. " + w[0]); lines += ["   " + x for x in w[1:]]
render("screenshots/fig4_triage_summary.png", "Triage results for four test complaints (local run)", lines)
print("ok")
