#!/bin/bash
# run-cda.sh - Convert YAML files to MDD and run OpenSOVD Classic Diagnostic Adapter
#
# Usage: ./run-cda.sh [options] <yaml-file> [yaml-file...]
#
# Options:
#   --no-docker    Only convert, don't run CDA
#   --port PORT    HTTP port for CDA (default: 8080)
#   --build        Force rebuild of CDA Docker image
#   --clean        Remove existing .mdd files before converting
#   -v, --verbose  Verbose output
#   -h, --help     Show this help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YAML_TO_MDD_DIR="$SCRIPT_DIR/yaml-to-mdd"
OUTPUT_DIR="$SCRIPT_DIR/.output"

# Defaults
PORT=20002
NO_DOCKER=false
VERBOSE=false
FORCE_BUILD=false
CLEAN=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [options] <yaml-file> [yaml-file...]"
    echo ""
    echo "Convert Diagnostic YAML files to MDD and run OpenSOVD Classic Diagnostic Adapter"
    echo ""
    echo "Options:"
    echo "  --no-docker    Only convert, don't run CDA"
    echo "  --port PORT    HTTP port for CDA (default: 20002)"
    echo "  --build        Force rebuild of CDA Docker image"
    echo "  --clean        Remove existing .mdd files before converting"
    echo "  -v, --verbose  Verbose output"
    echo "  -h, --help     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 yaml-schema/example-ecm.yml"
    echo "  $0 yaml-schema/example-ecm.yml yaml-schema/minimal-ecu.yml"
    echo "  $0 --port 9090 yaml-schema/*.yml"
    echo "  $0 --no-docker yaml-schema/example-ecm.yml"
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
YAML_FILES=()
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
        --clean)
            CLEAN=true
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
            YAML_FILES+=("$1")
            shift
            ;;
    esac
done

# Check input files
if [[ ${#YAML_FILES[@]} -eq 0 ]]; then
    error "No input YAML files specified"
    print_usage
    exit 1
fi

# Verify all files exist
for file in "${YAML_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        error "Input file not found: $file"
        exit 1
    fi
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Clean if requested
if [[ "$CLEAN" == true ]]; then
    log "Cleaning existing .mdd files..."
    rm -f "$OUTPUT_DIR"/*.mdd
fi

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

# Convert all YAML files to MDD
CONVERTED=0
FAILED=0
MDD_FILES=()

for yaml_file in "${YAML_FILES[@]}"; do
    # Resolve absolute path
    yaml_abs="$(cd "$(dirname "$yaml_file")" && pwd)/$(basename "$yaml_file")"
    
    # Generate output filename
    basename="${yaml_file##*/}"
    basename="${basename%.yml}"
    basename="${basename%.yaml}"
    mdd_file="$OUTPUT_DIR/${basename}.mdd"
    
    log "Converting $yaml_file -> $(basename "$mdd_file")"
    
    CONVERT_ARGS=("convert" "$yaml_abs" "-o" "$mdd_file" "--force")
    if [[ "$VERBOSE" == true ]]; then
        CONVERT_ARGS+=("-v")
    fi
    
    if $YAML_TO_MDD_CMD "${CONVERT_ARGS[@]}"; then
        MDD_FILES+=("$mdd_file")
        ((++CONVERTED))
    else
        error "Failed to convert: $yaml_file"
        ((++FAILED))
    fi
done

log "Conversion complete: $CONVERTED succeeded, $FAILED failed"

if [[ $CONVERTED -eq 0 ]]; then
    error "No files were converted successfully"
    exit 1
fi

# List generated MDD files
log "Generated MDD files in $OUTPUT_DIR:"
for mdd in "${MDD_FILES[@]}"; do
    echo "  - $(basename "$mdd")"
done

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
log "  Databases: $OUTPUT_DIR (${#MDD_FILES[@]} files)"

# Export port for docker-compose
export CDA_PORT="$PORT"

# Check if image exists
if ! docker image inspect diagnostic-yaml/cda:local &> /dev/null || [[ "$FORCE_BUILD" == true ]]; then
    log "Building CDA image (this may take a few minutes on first run)..."
    docker compose build
fi

log ""
log "Starting CDA at http://localhost:$PORT"
log "Press Ctrl+C to stop"
log ""

if [[ "$FORCE_BUILD" == true ]]; then
    docker compose up --build
else
    docker compose up
fi
