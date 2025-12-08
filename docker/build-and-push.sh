#!/bin/bash
# Build and push Docker image to Docker Hub

set -e

# Configuration
DOCKER_USERNAME="${DOCKER_USERNAME:-ranaislek}"
IMAGE_NAME="y6-practice-exam"
VERSION="${1:-latest}"

echo "=========================================="
echo "  Building Y6 Practice Exam Docker Image"
echo "=========================================="
echo ""
echo "Username: $DOCKER_USERNAME"
echo "Image: $IMAGE_NAME"
echo "Version: $VERSION"
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Build image
echo "Building image..."
docker build -t ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION} .

# Tag as latest if not already
if [ "$VERSION" != "latest" ]; then
    docker tag ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION} ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
fi

# Login to Docker Hub
echo ""
echo "Logging into Docker Hub..."
docker login

# Push images
echo ""
echo "Pushing images..."
docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}

if [ "$VERSION" != "latest" ]; then
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
fi

echo ""
echo "=========================================="
echo "  Done!"
echo "=========================================="
echo ""
echo "Image pushed:"
echo "  - ${DOCKER_USERNAME}/${IMAGE_NAME}:${VERSION}"
if [ "$VERSION" != "latest" ]; then
    echo "  - ${DOCKER_USERNAME}/${IMAGE_NAME}:latest"
fi
echo ""
echo "To deploy:"
echo "  docker pull ${DOCKER_USERNAME}/${IMAGE_NAME}:latest"
echo "  docker-compose -f docker-compose.simple.yml up -d"
