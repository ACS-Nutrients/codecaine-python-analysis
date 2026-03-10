aws dynamodb create-table \
    --table-name ChatbotData \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
        AttributeName=GSI1PK,AttributeType=S \
        AttributeName=GSI1SK,AttributeType=S \
    --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 \
    --global-secondary-indexes '[
        {
            "IndexName": "GSI1-Conversations",
            "KeySchema": [
                {"AttributeName":"GSI1PK","KeyType":"HASH"},
                {"AttributeName":"GSI1SK","KeyType":"RANGE"}
            ],
            "Projection": {"ProjectionType":"ALL"},
            "ProvisionedThroughput": {"ReadCapacityUnits":5,"WriteCapacityUnits":5}
        }
    ]' \
    --endpoint-url http://localhost:8000