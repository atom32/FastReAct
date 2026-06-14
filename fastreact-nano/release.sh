#!/bin/bash
#
# FastReAct Nano - Release Script
# Automates the packaging and release process
#
# Usage:
#   ./release.sh              # Interactive mode
#   ./release.sh patch        # Bump patch version (2.0.0 -> 2.0.1)
#   ./release.sh minor        # Bump minor version (2.0.0 -> 2.1.0)
#   ./release.sh major        # Bump major version (2.0.0 -> 3.0.0)
#   ./release.sh --build-only # Skip version bump, just build
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="fastreact-nano"
PYTHON_VERSIONS=("3.10" "3.11" "3.12")
BUILD_DIR="dist"
ARTIFACTS_DIR="release"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found"
        exit 1
    fi

    if ! command -v git &> /dev/null; then
        log_error "git not found"
        exit 1
    fi

    log_success "All dependencies found"
}

get_version() {
    grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' | tr -d '"'
}

bump_version() {
    local version=$1
    local bump_type=$2

    IFS='.' read -r major minor patch <<< "$version"

    case $bump_type in
        "patch")
            patch=$((patch + 1))
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        *)
            log_error "Invalid bump type: $bump_type"
            exit 1
            ;;
    esac

    echo "${major}.${minor}.${patch}"
}

update_version() {
    local new_version=$1

    log_info "Updating version to ${new_version}"

    # Update pyproject.toml
    sed -i.bak "s/^version = \".*\"/version = \"${new_version}\"/" pyproject.toml
    rm -f pyproject.toml.bak

    # Update __init__.py
    sed -i.bak "s/__version__ = \".*\"/__version__ = \"${new_version}\"/" src/fastreact/__init__.py
    rm -f src/fastreact/__init__.py.bak

    log_success "Version updated to ${new_version}"
}

run_tests() {
    log_info "Running tests..."

    if ! python3 -m pytest tests/ -v --tb=short; then
        log_error "Tests failed"
        exit 1
    fi

    log_success "All tests passed"
}

build_package() {
    local version=$1

    log_info "Building package ${PROJECT_NAME} v${version}..."

    # Clean build directories
    rm -rf ${BUILD_DIR} ${ARTIFACTS_DIR} *.egg-info
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete

    # Build source distribution
    python3 -m build --sdist --outdir ${BUILD_DIR}

    # Build wheel
    python3 -m build --wheel --outdir ${BUILD_DIR}

    log_success "Package built successfully"
}

create_artifacts() {
    local version=$1

    log_info "Creating release artifacts..."

    # Create artifacts directory
    mkdir -p ${ARTIFACTS_DIR}

    # Copy built packages
    cp -r ${BUILD_DIR}/* ${ARTIFACTS_DIR}/

    # Create checksums
    cd ${ARTIFACTS_DIR}
    shasum -a 256 *.tar.gz *.whl > SHA256SUMS
    cd ..

    # Create release notes template
    cat > ${ARTIFACTS_DIR}/RELEASE_NOTES.md <<EOF
# FastReAct Nano v${version} Release Notes

## Installation

\`\`\`bash
# From PyPI (after release)
pip install fastreact-nano==${version}

# With all features
pip install "fastreact-nano[all]==${version}"

# With specific features
pip install "fastreact-nano[cli,feishu,mcp]==${version}"
\`\`\`

## Docker Images

\`\`\`bash
# Pull image
docker pull fastreactnano/fastreact-nano:v${version}

# Run with Docker Compose
docker-compose up -d
\`\`\`

## What's Changed

<!-- Add release notes here -->

## SHA256 Checksums

\`\`\`
$(cat ${ARTIFACTS_DIR}/SHA256SUMS)
\`\`\`
EOF

    log_success "Release artifacts created in ${ARTIFACTS_DIR}/"
}

build_docker_images() {
    local version=$1

    log_info "Building Docker images..."

    # Build standard image
    docker build \
        --target production \
        --tag fastreactnano/fastreact-nano:v${version} \
        --tag fastreactnano/fastreact-nano:latest \
        --build-arg MCP_ENABLED=true \
        .

    # Build development image
    docker build \
        --target development \
        --tag fastreactnano/fastreact-nano:v${version}-dev \
        --build-arg MCP_ENABLED=true \
        .

    log_success "Docker images built successfully"
}

create_git_tag() {
    local version=$1

    log_info "Creating git tag v${version}..."

    # Commit version changes
    git add pyproject.toml src/fastreact/__init__.py
    git commit -m "chore: bump version to ${version}"

    # Create tag
    git tag -a "v${version}" -m "Release version ${version}"

    log_success "Git tag v${version} created"
}

publish_to_pypi() {
    log_warning "Skipping PyPI publish (requires manual confirmation)"
    log_info "To publish manually:"
    echo "  twine upload ${ARTIFACTS_DIR}/*"
}

publish_to_docker() {
    log_warning "Skipping Docker Hub publish (requires manual confirmation)"
    log_info "To publish manually:"
    echo "  docker push fastreactnano/fastreact-nano:v${VERSION}"
    echo "  docker push fastreactnano/fastreact-nano:latest"
}

# Main workflow
main() {
    local bump_type=""
    local build_only=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            patch|minor|major)
                bump_type=$1
                shift
                ;;
            --build-only)
                build_only=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [patch|minor|major] [--build-only]"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Print header
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}FastReAct Nano - Release Script${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""

    # Step 1: Check dependencies
    check_dependencies
    echo ""

    # Step 2: Get current version
    CURRENT_VERSION=$(get_version)
    log_info "Current version: ${CURRENT_VERSION}"
    echo ""

    # Step 3: Bump version (if not build-only)
    if [ "$build_only" = false ]; then
        if [ -z "$bump_type" ]; then
            echo "Select version bump type:"
            echo "  1) patch  (${CURRENT_VERSION} -> $(bump_version $CURRENT_VERSION patch))"
            echo "  2) minor  (${CURRENT_VERSION} -> $(bump_version $CURRENT_VERSION minor))"
            echo "  3) major  (${CURRENT_VERSION} -> $(bump_version $CURRENT_VERSION major))"
            echo "  4) skip version bump"
            echo ""
            read -p "Enter choice [1-4]: " choice

            case $choice in
                1) bump_type="patch" ;;
                2) bump_type="minor" ;;
                3) bump_type="major" ;;
                4) build_only=true ;;
                *)
                    log_error "Invalid choice"
                    exit 1
                    ;;
            esac
        fi

        if [ "$build_only" = false ]; then
            NEW_VERSION=$(bump_version $CURRENT_VERSION $bump_type)
            update_version $NEW_VERSION
            VERSION=$NEW_VERSION
        else
            VERSION=$CURRENT_VERSION
        fi
    else
        VERSION=$CURRENT_VERSION
    fi

    echo ""
    log_success "Releasing version: ${VERSION}"
    echo ""

    # Step 4: Run tests
    run_tests
    echo ""

    # Step 5: Build package
    build_package $VERSION
    echo ""

    # Step 6: Create artifacts
    create_artifacts $VERSION
    echo ""

    # Step 7: Build Docker images
    if command -v docker &> /dev/null; then
        build_docker_images $VERSION
        echo ""
    else
        log_warning "Docker not found, skipping Docker image build"
    fi

    # Step 8: Git tag (if version bumped)
    if [ "$build_only" = false ]; then
        create_git_tag $VERSION
        echo ""
    fi

    # Print summary
    echo ""
    echo -e "${GREEN}======================================${NC}"
    echo -e "${GREEN}Release Complete!${NC}"
    echo -e "${GREEN}======================================${NC}"
    echo ""
    log_info "Version: ${VERSION}"
    log_info "Artifacts: ${ARTIFACTS_DIR}/"
    log_info "Docker images:"
    echo "  - fastreactnano/fastreact-nano:v${VERSION}"
    echo "  - fastreactnano/fastreact-nano:v${VERSION}-feishu"
    echo "  - fastreactnano/fastreact-nano:v${VERSION}-dev"
    echo ""
    log_info "Next steps:"
    if [ "$build_only" = false ]; then
        echo "  1. Review the release: git diff"
        echo "  2. Push to GitHub: git push origin main && git push origin v${VERSION}"
        echo "  3. Create GitHub release"
        echo "  4. Publish to PyPI: twine upload ${ARTIFACTS_DIR}/*"
        echo "  5. Publish to Docker Hub: docker push fastreactnano/fastreact-nano:v${VERSION}"
    else
        echo "  1. Test the build artifacts"
        echo "  2. Publish to PyPI: twype upload ${ARTIFACTS_DIR}/*"
        echo "  3. Publish to Docker Hub: docker push fastreactnano/fastreact-nano:v${VERSION}"
    fi
    echo ""
}

# Run main function
main "$@"
