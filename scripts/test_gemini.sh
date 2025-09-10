#!/bin/bash
echo "🧪 Gemini Model Testi..."

# Health check
echo "1. Health check..."
curl -s http://localhost:8000/api/health | jq .

echo -e "\n2. Chat test..."
response=$(curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{
        "session_id": "test-gemini-001",
        "message": "Assalomu alaykum! Abonement turlari va narxlari haqida ma'\''lumot bering."
    }')

echo "$response" | jq .

echo -e "\n3. Follow-up test..."
curl -s -X POST http://localhost:8000/api/chat \
    -H "Content-Type: application/json" \
    -d '{
        "session_id": "test-gemini-001", 
        "message": "Premium abonement sotib olishni istayman"
    }' | jq -r '.answer'

echo -e "\n✅ Test tugadi!"
