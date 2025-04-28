#!/bin/bash
set -e

# Deploy script for SentinelIQ
# This script automates the deployment process for SentinelIQ

echo "🚀 Starting SentinelIQ deployment process..."

# Check if running from the project root
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: This script must be run from the project root directory"
    exit 1
fi

# Pull latest changes from Git repository
echo "📥 Pulling latest changes from Git repository..."
git pull

# Create/update .env file
if [ ! -f ".env" ]; then
    echo "🔑 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️ Please update the .env file with your production credentials"
    exit 1
fi

# Build and start Docker containers
echo "🐳 Building and starting Docker containers..."
docker-compose down
docker-compose pull
docker-compose up -d --build

# Apply database migrations
echo "🔄 Applying database migrations..."
docker-compose exec -T web poetry run python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
docker-compose exec -T web poetry run python manage.py collectstatic --noinput

# Perform system cleanup
echo "🧹 Cleaning up unused Docker resources..."
docker system prune -f

echo "✅ Deployment completed successfully!"
echo "🔗 Your application should be available at http://your-server-ip" 