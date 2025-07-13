# image_resizer/handler.py

import os
import boto3
from PIL import Image
from io import BytesIO

UPLOAD_BUCKET = os.environ['UPLOAD_BUCKET_NAME']
RESIZE_BUCKET = os.environ['RESIZE_BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
REGION = os.environ.get('REGION', "eu-central-1")


s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        detail = event['detail']
        bucket_name = detail['bucket']['name']
        object_key = detail['object']['key']

        if bucket_name != UPLOAD_BUCKET:
            raise ValueError(f"Ignoring object from unexpected bucket: {bucket_name}")

        image_id = os.path.splitext(os.path.basename(object_key))[0]
        print(f"Processing image {object_key} for ImageID: {image_id}")

        s3_response = s3.get_object(Bucket=UPLOAD_BUCKET, Key=object_key)
        image_data = s3_response['Body'].read()
        image = Image.open(BytesIO(image_data))

        image.thumbnail((128, 128))
        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        buffer.seek(0)

        resized_key = f"resized/{object_key}"
        s3.put_object(
            Bucket=RESIZE_BUCKET,
            Key=resized_key,
            Body=buffer,
            ContentType='image/jpeg'
        )

        table.put_item(
            Item={
                'ImageID': image_id,
                'original_s3_key': object_key,
                'resized_s3_key': resized_key,
                'status': 'resized'
            }
        )

        return {
            'status': 'resized',
            'ImageID': image_id,
            'original_s3_key': object_key,
            'resized_s3_key': resized_key
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }