import os
import boto3
import botocore
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
AWS_BUCKET_NAME = os.environ['AWS_BUCKET_NAME']


# Initialize AWS S3 client
s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

class Aws():
    """Class for AWS methods"""

    @classmethod
    def get_file_url(cls, file_name):
        try:
            # Generate a pre-signed URL for the file
            url = s3.generate_presigned_url('get_object',
                                            Params={'Bucket': AWS_BUCKET_NAME,
                                                    'Key': file_name}
                                                    )  # URL expiration time in seconds (7 days)

            # Return the URL as a JSON response
            return url
        except botocore.exceptions.NoCredentialsError:
            return 'Error: AWS credentials not found.', 500
        except botocore.exceptions.ParamValidationError:
            return 'Error: Invalid bucket or file name.', 400
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return 'Error: File not found.', 404
            else:
                return 'Error: Failed to retrieve file URL.', 500

    @classmethod
    def upload_file(cls, file):
        file_name = file.filename
        s3.upload_fileobj(file, AWS_BUCKET_NAME, file_name,ExtraArgs={'ContentType': "image/jpeg"})
        return file_name
