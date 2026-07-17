import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

rekognition = boto3.client('rekognition')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Your DynamoDB Table name')

def lambda_handler(event, context):
    try:
        # 1. Safely handle empty query parameters
        query_params = event.get('queryStringParameters') or {} 
        bucket = query_params.get('bucket')
        key = query_params.get('key')
        
        if not bucket or not key:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Missing bucket or key query parameters in the URL'})
            }

        # 2. Call Amazon Rekognition
        response = rekognition.recognize_celebrities(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            }
        )

        # 3. Parse results into two formats (one for DB, one for JSON)
        celebrities_for_json = []
        celebrities_for_db = []
        
        for celeb in response.get('CelebrityFaces', []):
            conf_float = round(celeb['MatchConfidence'], 2)
            
            # Standard float for the browser response
            celebrities_for_json.append({
                'celebrity': celeb['Name'],
                'confidence': conf_float 
            })
            
            # Decimal format for DynamoDB
            celebrities_for_db.append({
                'celebrity': celeb['Name'],
                'confidence': Decimal(str(conf_float)) 
            })

        # 4. Store request history and results in DynamoDB
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        table.put_item(
            Item={
                'RequestId': request_id,
                'Timestamp': timestamp,
                'S3Bucket': bucket,
                'S3Key': key,
                'DetectedCelebrities': celebrities_for_db, # Use the Decimal version here
                'UnrecognizedFacesCount': len(response.get('UnrecognizedFaces', []))
            }
        )

        # 5. Return the JSON response to the user
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'results': celebrities_for_json}) # Use the float version here
        }

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
