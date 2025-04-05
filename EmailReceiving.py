import boto3
import base64
import os
import email
from email import policy
from email.parser import BytesParser

# Initialize the S3 client
s3_client = boto3.client('s3')

# The S3 bucket name is set as an environment variable in your Lambda configuration
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'your-default-bucket-name')

def lambda_handler(event, context):
    """
    Lambda function to extract attachments from an email and upload them to S3.
    The email subject is used as the parent folder name (e.g., "CS260").
    Attachments whose file names contain 'lecture', 'hw', or 'written assignment'
    are uploaded to a subfolder (e.g., "lecture") within the subject folder.
    """
    
    # Assume the raw email content is provided as a base64 encoded string in the event.
    # In practice, you may retrieve the email from an S3 trigger or SES event.
    raw_email_b64 = event.get('content')
    if not raw_email_b64:
        print("No email content provided in the event.")
        return {"status": "error", "message": "Missing email content"}
    
    try:
        # Decode the base64 email string to bytes
        email_bytes = base64.b64decode(raw_email_b64)
        
        # Parse the email using the default policy
        msg = BytesParser(policy=policy.default).parsebytes(email_bytes)
    except Exception as e:
        print(f"Error parsing email: {e}")
        return {"status": "error", "message": "Failed to parse email"}
    
    # Get the email subject; this will be used as the parent folder name
    subject = msg.get('Subject')
    if not subject:
        print("Email does not have a subject.")
        return {"status": "error", "message": "Missing email subject"}
    
    # Clean up the subject to use as a folder name (e.g., trim whitespace)
    subject_folder = subject.strip()
    
    # Define the mapping of keywords to S3 subfolder names.
    # You can adjust the keywords and target folder names as needed.
    keyword_mapping = {
        "lecture": "lecture",
        "hw": "hw",
        "written assignment": "written assignment"
    }
    
    uploaded_files = []
    
    # Iterate over all parts of the email to find attachments
    for part in msg.iter_attachments():
        filename = part.get_filename()
        if not filename:
            continue  # Skip parts without a filename
        
        # Determine the target subfolder based on attachment file name.
        # Convert the file name to lower case to ensure case-insensitive matching.
        lower_filename = filename.lower()
        target_subfolder = None
        
        for keyword, folder_name in keyword_mapping.items():
            if keyword in lower_filename:
                target_subfolder = folder_name
                break  # Use the first matching keyword
        
        if target_subfolder:
            # Construct the S3 key using the email subject and the attachment category
            s3_key = f"{subject_folder}/{target_subfolder}/{filename}"
            
            try:
                # Get the attachment content as bytes
                file_data = part.get_payload(decode=True)
                # Upload the file to the specified S3 bucket and key
                s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_data)
                print(f"Uploaded {filename} to s3://{BUCKET_NAME}/{s3_key}")
                uploaded_files.append(s3_key)
            except Exception as e:
                print(f"Failed to upload {filename}: {e}")
        else:
            print(f"Attachment {filename} did not match any expected keywords.")
    
    return {
        "status": "success",
        "uploaded_files": uploaded_files
    }
