#!/bin/bash
# FastReAct Nano Release Script
# Automates version bump, changelog update, and package building

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Get current version
get_current_version() {
    grep "^__version__" src/fastreact/__init__.py | cut -d'"' -f2
}

# Update version in __init__.py
update_version_init() {
    local new_version=$1
    sed -i.bak "s/__version__ = \".*\"/__version__ = \"$new_version\"/" src/fastreact/__init__.py
    rm -f src/fastreact/__init__.py.bak
    log_success "Updated __init__.py to v$new_version"
}

# Update version in pyproject.toml
update_version_pyproject() {
    local new_version=$1
    if [ -f pyproject.toml ]; then
        sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
        rm -f pyproject.toml.bak
        log_success "Updated pyproject.toml to v$new_version"
    fi
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."

    if [ ! -d "frontend" ]; then
        log_error "Frontend directory not found"
        exit 1
    fi

    cd frontend

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        log_info "Installing frontend dependencies..."
        npm install
    fi

    # Build frontend
    log_info "Running npm run build..."
    npm run build

    if [ ! -d "dist" ]; then
        log_error "Frontend build failed - dist directory not created"
        exit 1
    fi

    log_success "Frontend built successfully ($(du -sh dist | cut -f1))"

    cd ..
}

# Create changelog entry
update_changelog() {
    local version=$1
    local date=$(date +%Y-%m-%d)

    if [ ! -f "CHANGELOG.md" ]; then
        touch CHANGELOG.md
    fi

    # Create changelog entry
    cat > CHANGELOG.md.tmp << EOF
# Changelog

## [$version] - $date

### Features
- Vue 3 Frontend: Modern SPA with Chat and Admin interfaces
- MCP Tool Marketplace: 12 tools across 8 categories
- Real-time Dashboard: System metrics and session monitoring
- Configuration Editor: Visual LLM, MCP, and Agent settings
- Session Manager: Complete session lifecycle management
- Dark Mode: Full theme support

### Improvements
- Responsive design for mobile and tablet
- WebSocket event streaming
- REST API for configuration and metrics
- Build optimization with code splitting

### Fixes
- Fixed TypeScript compilation issues
- Fixed icon imports (Robot → Avatar, Server → Monitor)
- Fixed TailwindCSS v4 configuration

### Documentation
- Added Phase 2 implementation summaries
- Updated README with frontend usage
- Added component documentation

EOF

    # Append existing changelog
    if [ -s "CHANGELOG.md" ]; then
        tail -n +2 CHANGELOG.md >> CHANGELOG.md.tmp
    fi

    mv CHANGELOG.md.tmp CHANGELOG.md
    log_success "Updated CHANGELOG.md"
}

# Build Python package
build_package() {
    log_info "Building Python package..."

    # Clean previous builds
    rm -rf dist/ build/ *.egg-info

    # Build source distribution
    python -m build --sdist

    # Build wheel (optional)
    if command -v twine &> /dev/null; then
        log_info "Building wheel..."
        python -m build --wheel
    fi

    log_success "Package built successfully"
    ls -lh dist/
}

# Run tests
run_tests() {
    log_info "Running tests..."

    if [ -f "run_tests.py" ]; then
        python run_tests.py unit
    else
        log_warning "No test runner found, skipping tests"
    fi
}

# Git operations
git_operations() {
    local version=$1

    log_info "Creating git tag..."

    # Check if git repo
    if [ ! -d ".git" ]; then
        log_warning "Not a git repository, skipping git operations"
        return
    fi

    # Create git tag
    git tag -a "v$version" -m "Release v$version - The Visual Update"

    log_success "Git tag created: v$version"
    echo ""
    log_info "To push changes:"
    echo "  git push"
    echo "  git push origin v$version"
}

# Main release process
main() {
    local version_type=${1:-}
    local current_version
    local new_version

    echo ""
    echo "=========================================="
    echo "  FastReAct Nano Release Script"
    echo "=========================================="
    echo ""

    # Get current version
    current_version=$(get_current_version)
    log_info "Current version: $current_version"

    # Determine new version
    if [ -z "$version_type" ]; then
        echo ""
        echo "Select version bump type:"
        echo "  1) patch (x.x.X)"
        echo "  2) minor (x.X.x)"
        echo "  3) major (X.x.x)"
        echo "  4) custom"
        echo ""
        read -p "Enter choice [1-4]: " choice

        case $choice in
            1) version_type="patch" ;;
            2) version_type="minor" ;;
            3) version_type="major" ;;
            4)
                read -p "Enter custom version (e.g., 2.3.0): " version_type
                ;;
            *)
                log_error "Invalid choice"
                exit 1
                ;;
        esac
    fi

    # Calculate new version
    if [[ "$version_type" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        new_version=$version_type
    else
        IFS='.' read -ra VERSION <<< "$current_version"
        major=${VERSION[0]}
        minor=${VERSION[1]}
        patch=${VERSION[2]}

        case $version_type in
            patch)
                patch=$((patch + 1))
                ;;
            minor)
                minor=$((minor + 1))
                patch=0
                ;;
            major)
                major=$((major + 1))
                minor=0
                patch=0
                ;;
        esac

        new_version="$major.$minor.$patch"
    fi

    echo ""
    log_info "New version: $new_version"
    echo ""

    # Confirmation
    read -p "Continue with release v$new_version? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "Release cancelled"
        exit 0
    fi

    echo ""
    log_info "Starting release process for v$new_version..."
    echo ""

    # Build frontend
    build_frontend

    echo ""

    # Update version files
    update_version_init "$new_version"
    update_version_pyproject "$new_version"

    echo ""

    # Update changelog
    update_changelog "$new_version"

    echo ""

    # Run tests
    run_tests

    echo ""

    # Build package
    build_package

    echo ""

    # Git operations
    git_operations "$new_version"

    echo ""
    echo "=========================================="
    log_success "Release v$new_version complete!"
    echo "=========================================="
    echo ""
    log_info "Next steps:"
    echo "  1. Review changes in git"
    echo "  2. Commit changes: git commit -am \"Release v$new_version\""
    echo "  3. Push to git: git push && git push origin v$new_version"
    echo "  4. Publish to PyPI: twine upload dist/*"
    echo ""
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            build_frontend
            build_package
            exit 0
            ;;
        --version)
            shift
            version_type="$1"
            ;;
        -h|--help)
            echo "Usage: $0 [patch|minor|major|custom-version]"
            echo ""
            echo "Options:"
            echo "  --build-only    Only build frontend and package (no version bump)"
            echo "  --version VER  Set specific version"
            echo "  -h, --help     Show this help"
            echo ""
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use -h for help"
            exit 1
            ;;
    esac
    shift
done

# Run main
main "$version_type"
