import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

endpoint_url = os.getenv("R2_ENDPOINT_URL")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
bucket_name = os.getenv("R2_BUCKET_NAME")

print("Testing Cloudflare R2 Connection...")
print(f"Endpoint: {endpoint_url}")
print(f"Bucket:   {bucket_name}\n")

s3_client = boto3.client(
    service_name="s3",
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="auto",
)

try:
    # Check if the specific bucket exists and your token has access to it
    s3_client.head_bucket(Bucket=bucket_name)
    print("✅ Connection successful! R2 credentials and bucket access verified.")

except ClientError as err:
    error_code = err.response.get("Error", {}).get("Code")
    if error_code == "404":
        print("❌ Connected, but the specified bucket does not exist.")
    elif error_code == "403":
        print("❌ Authentication failed. Check your Access Key ID and Secret Access Key.")
    else:
        print(f"❌ Connection failed with error: {err}")
except Exception as exc:
    print(f"❌ Unexpected error connecting to R2: {exc}")