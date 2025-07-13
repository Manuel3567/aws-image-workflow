import os
import json
from moto import mock_aws
import boto3
import pytest
from PIL import Image
from io import BytesIO

# Patch environment variables before importing the handler
os.environ['UPLOAD_BUCKET_NAME'] = 'imageworkflow-prod-upload-bucket-123456789101'
os.environ['RESIZE_BUCKET_NAME'] = 'imageworkflow-prod-resize-bucket-123456789101'
os.environ['TABLE_NAME'] = 'ImageMetadataTable'
os.environ['REGION'] = 'eu-central-1'


@pytest.fixture
def event():
    with open('tests/s3_event.json') as f:
        return json.load(f)


@pytest.fixture
def dummy_image_bytes():
    img = Image.new('RGB', (500, 500), color='blue')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.getvalue()


@mock_aws
def test_lambda_handler(event, dummy_image_bytes):
    # Setup mock S3
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket=os.environ['UPLOAD_BUCKET_NAME'])
    s3.create_bucket(Bucket=os.environ['RESIZE_BUCKET_NAME'])

    # Upload dummy image to simulate S3 trigger
    s3.put_object(
        Bucket=os.environ['UPLOAD_BUCKET_NAME'],
        Key=event['detail']['object']['key'],
        Body=dummy_image_bytes,
        ContentType='image/jpeg'
    )

    # Setup mock DynamoDB
    region = os.environ['REGION']
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table_name = os.environ['TABLE_NAME']

    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'ImageID', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'ImageID', 'AttributeType': 'S'},
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5,
        }
    )
    from image_resizer import handler  # import after env is set

    # Run the handler
    result = handler.lambda_handler(event, context={})

    # Assertions
    assert result['status'] == 'resized'
    assert result['ImageID'] == "0dde45c1-4c61-4084-946a-4f24bf0068a9"

    # Check resized object exists
    response = s3.get_object(
        Bucket=os.environ['RESIZE_BUCKET_NAME'],
        Key=f"resized/{event['detail']['object']['key']}"
    )
    assert response['ContentType'] == 'image/jpeg'

    # Read the image bytes
    image_bytes = response['Body'].read()

    # Load with PIL
    image = Image.open(BytesIO(image_bytes))

    # Assert size
    assert image.size[0] == 128 and image.size[1] == 128, f"Image size is {image.size}, expected 128x128"