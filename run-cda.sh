#!/bin/bash
# run-cda.sh - Convert YAML to MDD and run OpenSOVD Classic Diagnostic Adapter
#
# Usage: ./run-cda.sh <yaml-file> [options]
#
# Options:
#   --no-docker    Only convert, don't run CDA
#   --port PORT    HTTP port for CDA (default: 8080)
#   --image IMAGE  Docker image to use (default: ghcr.io/eclipse-opensovd/classic-diagnostic-adapter:latest)
#   -v, --verbose  Verbose output
#   -h, --help     Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YAML_TO_MDD_DIR="$SCRIPT_DIR/yaml-to-mdd"
OUTPUT_DIR="$SCRIPT_DIR/.output"

# Defaults
PORT=8080
DOCKER_IMAGE="ghcr.io/eclipse-opensovd/classic-diagnostic-adapter:latest"
NO_DOCKER=false
VERBOSE=false

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
    echo "  --image IMAGE  Docker image to use"
    echo "  -v, --verbose  Verbose output"
    echo "  -h, --help     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 example-ecm.yml"
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
        --image)
            DOCKER_IMAGE="$2"
            shift 2
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
YAML_BASENAME="$(basename "$YAML_FILE" .yml)"
YAML_BASENAME="$(basename "$YAML_BASENAME" .yaml)"

# Create output directory
mkdir -p "$OUTPUT_DIR"
MDD_FILE="$OUTPUT_DIR/${YAML_BASENAME}.mdd"

# Check if yaml-to-mdd is installed
log "Checking yaml-to-mdd installation..."
if ! command -v yaml-to-mdd &> /dev/null; then
    warn "yaml-to-mdd not found in PATH, attempting to install..."
    
    if [[ -d "$YAML_TO_MDD_DIR" ]]; then
        log "Installing yaml-to-mdd from $YAML_TO_MDD_DIR"
        
        # Try poetry first, then pip
        if command -v poetry &> /dev/null; then
            (cd "$YAML_TO_MDD_DIR" && poetry install)
            # Use poetry run for the command
            YAML_TO_MDD_CMD="poetry -C $YAML_TO_MDD_DIR run yaml-to-mdd"
        else
            pip install -e "$YAML_TO_MDD_DIR"
            YAML_TO_MDD_CMD="yaml-to-mdd"
        fi
    else
        error "yaml-to-mdd directory not found: $YAML_TO_MDD_DIR"
        exit 1
    fi
else
    YAML_TO_MDD_CMD="yaml-to-mdd"
fi

# Convert YAML to MDD
log "Converting $YAML_FILE to MDD..."
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
    exit 0
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker not found. Install Docker or use --no-docker"
    exit 1
fi

# Run CDA
log "Starting OpenSOVD Classic Diagnostic Adapter..."
log "  Image: $DOCKER_IMAGE"
log "  Port: $PORT"
log "  MDD: $MDD_FILE"

CONTAINER_NAME="cda-${YAML_BASENAME}-$$"

# Pull image if needed
if [[ "$VERBOSE" == true ]]; then
    log "Pulling Docker image..."
    docker pull "$DOCKER_IMAGE"
fi

# Run container
log "Starting container..."
docker run --rm \
    --name "$CONTAINER_NAME" \
    -p "${PORT}:8080" \
    -v "$MDD_FILE:/data/ecu.mdd:ro" \
    "$DOCKER_IMAGE"
