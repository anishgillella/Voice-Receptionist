#!/bin/bash

# Setup ngrok tunnel for voice agent backend
# This exposes the local FastAPI server publicly so SendGrid can reach our webhook

echo "=========================================="
echo "Setting up ngrok tunnel for Voice Agent"
echo "=========================================="

# Start ngrok in the background
echo "Starting ngrok tunnel on port 8000..."
ngrok http 8000 > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start and get the public URL
sleep 3

# Extract the public URL from ngrok
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null)

if [ -z "$PUBLIC_URL" ]; then
    echo "❌ Failed to get ngrok URL. Make sure ngrok is installed and running."
    echo "   Install with: brew install ngrok"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✅ ngrok tunnel established!"
echo "=========================================="
echo "PUBLIC URL: $PUBLIC_URL"
echo "=========================================="
echo ""

# Generate SendGrid webhook URL
WEBHOOK_URL="$PUBLIC_URL/webhooks/sendgrid/inbound-parse"

echo "📧 SendGrid Configuration"
echo "=========================================="
echo ""
echo "1. Go to SendGrid Dashboard"
echo "   https://app.sendgrid.com/settings/mail_settings"
echo ""
echo "2. Click on 'Inbound Parse'"
echo ""
echo "3. Add a new host (or update existing):"
echo "   Hostname: replies.yourdomain.com (or any subdomain)"
echo "   URL: $WEBHOOK_URL"
echo ""
echo "4. In SendGrid, set up an MX record for your domain:"
echo "   Name: replies"
echo "   Type: MX"
echo "   Priority: 10"
echo "   Value: mx.sendgrid.net"
echo ""
echo "5. Test by replying to an email from InsureFlow Solutions"
echo "   Your reply will automatically:"
echo "   ✅ Get analyzed by LLM"
echo "   ✅ Generate smart response"
echo "   ✅ Send auto-reply in same thread"
echo ""
echo "=========================================="
echo ""
echo "💡 To stop the tunnel, kill ngrok:"
echo "   pkill ngrok"
echo ""
echo "Keeping ngrok running for webhook traffic..."
echo "Press Ctrl+C to stop."
echo ""

# Keep the script running
tail -f /tmp/ngrok.log &
wait
