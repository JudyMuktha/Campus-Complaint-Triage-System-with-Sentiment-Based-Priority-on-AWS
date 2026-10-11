AWS-CCTS: Campus Complaint Triage System - Mini Project Report
Judy Muktha P | Roll No 25IT1182 | Register No 312425205091

Files
- AWS-CCTS_Mini_Project_Report.docx  Final report (Word)
- AWS-CCTS_Mini_Project_Report.pdf   Same report as PDF
- lambda_function.py                 AWS Lambda source code (Python 3.12, boto3)
- test_harness.py                    Runs the Lambda code locally with simulated Comprehend, DynamoDB and SNS
- render_outputs.py                  Turns the test run results into the output images
- run_output.json                    Raw results of the test run
- screenshots/                       Output images used in Section 10

Run the local test:  python test_harness.py   (no AWS account needed)
