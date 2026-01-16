#!/usr/bin/env bash
# Monitor Cloudflare zone activation and certificate status

ZONE_ID="20801ec38271b007c779b54ccfddf542"
EMAIL="tzervas@vectorweight.com"
API_KEY=$(cat ~/Documents/.secret/cf-global-cpi-key)

echo "🔄 Monitoring Cloudflare zone activation and certificate status..."
echo "   Press Ctrl+C to stop"
echo ""

while true; do
    # Check zone status
    STATUS=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}" \
        -H "X-Auth-Email: ${EMAIL}" \
        -H "X-Auth-Key: ${API_KEY}" \
        -H "Content-Type: application/json" | jq -r '.result.status')
    
    # Check certificate status
    READY_CERTS=$(kubectl get certificates -n cert-manager --no-headers 2>/dev/null | grep -c "True" || echo "0")
    TOTAL_CERTS=$(kubectl get certificates -n cert-manager --no-headers 2>/dev/null | wc -l)
    
    # Check NS propagation
    NS=$(dig NS vectorweight.com +short 2>/dev/null | head -1)
    
    TIMESTAMP=$(date '+%H:%M:%S')
    
    echo -ne "\r[$TIMESTAMP] Zone: $STATUS | NS: ${NS:-checking...} | Certs: $READY_CERTS/$TOTAL_CERTS ready    "
    
    if [[ "$STATUS" == "active" ]]; then
        echo ""
        echo "🎉 Cloudflare zone is now ACTIVE!"
        echo "   Certificates should start issuing automatically."
        notify-send "Cloudflare Active" "Zone vectorweight.com is now active!" 2>/dev/null || true
        break
    fi
    
    sleep 30
done
