#!/bin/bash
# run-cda.sh - Convert YAML to MDD and run OpenSOVD Classic Diagnostic Adapter
#
# Usage: ./run-cda.sh <yaml-file> [options]
#
# Options:
#   --no-docker    Only convert, don't run CDA
#   --port PORT    HTTP port for CDA (default: 8080)
#   --build        Force rebuild of CDA Docker image
#   -v, --verbose  Verbose output
#   -h, --help     Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YAML_TO_MDD_DIR="$SCRIPT_DIR/yaml-to-mdd"
OUTPUT_DIR="$SCRIPT_DIR/.output"

# Defaults
PORT=8080
NO_DOCKER=false
VERBOSE=false
FORCE_BUILD=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 <yaml-file> [options]"
    echo ""
    echo "Convert Diagnostic YAML to MDD and run OpenSOVD Classic Diagnostic Adapter"
    echo ""
    echo "Options:"
    echo "  --no-docker    Only convert, don't run CDA"
    echo "  --port PORT    HTTP port for CDA (default: 8080)"
    echo "  --build        Force rebuild of CDA Docker image"
    echo "  -v, --verbose  Verbose output"
    echo "  -h, --help     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 yaml-schema/example-ecm.yml"
    echo "  $0 my-ecu.yaml --port 9090"
    echo "  $0 my-ecu.yaml --no-docker"
}

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Parse arguments
YAML_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        --no-docker)
            NO_DOCKER=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --build)
            FORCE_BUILD=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -*)
            error "Unknown option: $1"
            print_usage
            exit 1
            ;;
        *)
            if [[ -z "$YAML_FILE" ]]; then
                YAML_FILE="$1"
            else
                error "Multiple input files specified"
                print_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Check input file
if [[ -z "$YAML_FILE" ]]; then
    error "No input YAML file specified"
    print_usage
    exit 1
fi

if [[ ! -f "$YAML_FILE" ]]; then
    error "Input file not found: $YAML_FILE"
    exit 1
fi

# Resolve absolute path
YAML_FILE="$(cd "$(dirname "$YAML_FILE")" && pwd)/$(basename "$YAML_FILE")"

# Create output directory
mkdir -p "$OUTPUT_DIR"
MDD_FILE="$OUTPUT_DIR/ecu.mdd"

# Check if yaml-to-mdd is installed
log "Checking yaml-to-mdd installation..."
YAML_TO_MDD_CMD=""

if command -v yaml-to-mdd &> /dev/null; then
    YAML_TO_MDD_CMD="yaml-to-mdd"
elif command -v poetry &> /dev/null && [[ -f "$YAML_TO_MDD_DIR/pyproject.toml" ]]; then
    log "Using poetry to run yaml-to-mdd..."
    (cd "$YAML_TO_MDD_DIR" && poetry install --quiet 2>/dev/null || true)
    YAML_TO_MDD_CMD="poetry -C $YAML_TO_MDD_DIR run yaml-to-mdd"
elif [[ -d "$YAML_TO_MDD_DIR" ]]; then
    warn "yaml-to-mdd not found, installing with pip..."
    pip install -e "$YAML_TO_MDD_DIR" --quiet
    YAML_TO_MDD_CMD="yaml-to-mdd"
else
    error "yaml-to-mdd not found and cannot be installed"
    exit 1
fi

# Convert YAML to MDD
log "Converting $(basename "$YAML_FILE") to MDD..."
CONVERT_ARGS=("convert" "$YAML_FILE" "-o" "$MDD_FILE")
if [[ "$VERBOSE" == true ]]; then
    CONVERT_ARGS+=("-v")
fi

if $YAML_TO_MDD_CMD "${CONVERT_ARGS[@]}"; then
    log "MDD file created: $MDD_FILE"
else
    error "Conversion failed"
    exit 1
fi

# Stop here if --no-docker
if [[ "$NO_DOCKER" == true ]]; then
    log "Done (--no-docker specified)"
    echo ""
    echo "To run CDA manually:"
    echo "  CDA_PORT=$PORT docker compose up"
    exit 0
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker not found. Install Docker or use --no-docker"
    exit 1
fi

# Check docker compose
if ! docker compose version &> /dev/null; then
    error "Docker Compose not found. Install Docker Compose plugin or use --no-docker"
    exit 1
fi

# Build/run with docker compose
cd "$SCRIPT_DIR"

log "Starting OpenSOVD Classic Diagnostic Adapter..."
log "  Port: $PORT"
log "  MDD: $MDD_FILE"

# Export port for docker-compose
export CDA_PORT="$PORT"

# Build options
BUILD_ARGS=""
if [[ "$FORCE_BUILD" == true ]]; then
    BUILD_ARGS="--build"
fi

# Check if image exists
if ! docker image inspect diagnostic-yaml/cda:local &> /dev/null || [[ "$FORCE_BUILD" == true ]]; then
    log "Building CDA image (this may take a few minutes on first run)..."
    docker compose build
fi

log ""
log "Starting CDA at http://localhost:$PORT"
log "Press Ctrl+C to stop"
log ""

docker compose up $BUILD_ARGS
