#!/bin/bash

echo "🚀 PDF RAG System - Quick Start"
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check for .env file
cd infrastructure/docker
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "📝 IMPORTANT: Edit infrastructure/docker/.env and add your API keys:"
    echo "   - OPENAI_API_KEY (required)"
    echo "   - AWS credentials (optional - for S3 storage)"
    echo ""
    read -p "Press Enter after you've updated .env file..."
fi

echo "🔨 Building and starting containers..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "✅ PDF RAG System is starting!"
echo ""
echo "📍 Access points:"
echo "   - Frontend:  http://localhost:80"
echo "   - Backend:   http://localhost:5000"
echo "   - Streamlit: http://localhost:8501"
echo "   - API Docs:  http://localhost:5000/health/"
echo ""
echo "📋 Useful commands:"
echo "   - View logs:    docker-compose logs -f"
echo "   - Stop:         docker-compose down"
echo "   - Restart:      docker-compose restart"
echo ""
echo "🎉 Happy querying!"
