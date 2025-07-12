import os
import boto3
from PIL import Image
from io import BytesIO

# Load environment variables
UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET_NAME']
RESIZE_BUCKET = os.environ['RESIZE_BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']

# AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    image_id = event['ImageID']
    original_key = event['s3_key']
    
    print(f"Processing image {original_key} for ImageID: {image_id}")

    try:
        # 1. Download the original image from S3
        s3_response = s3.get_object(Bucket=UPLOAD_BUCKET, Key=original_key)
        image_data = s3_response['Body'].read()
        image = Image.open(BytesIO(image_data))

        # 2. Resize the image (example: thumbnail 128x128)
        image.thumbnail((128, 128))
        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        buffer.seek(0)

        # 3. Upload resized image to the resize bucket
        resized_key = f"resized/{original_key}"
        s3.put_object(
            Bucket=RESIZE_BUCKET,
            Key=resized_key,
            Body=buffer,
            ContentType='image/jpeg'
        )

        # 4. Update metadata in DynamoDB
        table.put_item(
            Item={
                'ImageID': image_id,
                'original_s3_key': original_key,
                'resized_s3_key': resized_key,
                'status': 'resized'
            }
        )

        return {
            'status': 'resized',
            'ImageID': image_id,
            'original_s3_key': original_key,
            'resized_s3_key': resized_key
        }

    except Exception as e:
        print(f"Error processing image {original_key}: {str(e)}")
        return {
            'status': 'error',
            'ImageID': image_id,
            'message': str(e)
        }