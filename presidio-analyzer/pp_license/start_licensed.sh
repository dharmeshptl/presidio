#!/bin/bash
# Simple startup script with license validation

echo "🔐 Presidio Analyzer - Licensed Startup"
echo "======================================"

# Check if license key exists
if [ -z "$LICENSE_KEY" ]; then
    echo "⚠️  No LICENSE_KEY found in environment"
    
    # Check if .license file exists
    if [ -f ".license" ]; then
        echo "📄 Found .license file, loading..."
        source .license
        if [ -n "$LICENSE_KEY" ]; then
            echo "✅ License loaded from file"
        fi
    fi
    
    # If still no license, generate one
    if [ -z "$LICENSE_KEY" ]; then
        echo "🔧 Generating new license key..."
        python3 license_generator.py
        echo ""
        echo "🔄 Please run this script again after setting the LICENSE_KEY"
        exit 1
    fi
fi

# Start the application
echo "🚀 Starting Presidio Analyzer..."
python3 app_pp.py