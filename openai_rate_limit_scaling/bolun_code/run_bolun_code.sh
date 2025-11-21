#!/bin/bash

# Exit on error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Bolun API Scaling Testing${NC}"
echo -e "${BLUE}========================================${NC}"

# Create timestamp
TIMESTAMP=$(date +"%Y_%m_%d-%H:%M:%S")
OUTPUT_DIR="$SCRIPT_DIR/outputs/$TIMESTAMP"

echo -e "${GREEN}Creating output directory: ${OUTPUT_DIR}${NC}"
mkdir -p "$OUTPUT_DIR"

# Change to bolun_code directory (where the data files are)
cd "$SCRIPT_DIR"

# Check if venv exists in parent directory
if [ ! -d "$PARENT_DIR/venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at $PARENT_DIR/venv${NC}"
    echo "Please create a virtual environment in the parent directory first."
    exit 1
fi

# Activate virtual environment from parent directory
echo -e "${GREEN}Activating virtual environment...${NC}"
source "$PARENT_DIR/venv/bin/activate"

# Verify required packages
echo -e "${GREEN}Checking dependencies...${NC}"
python -c "import pandas, openai, opik, dotenv, openpyxl" 2>/dev/null || {
    echo -e "${RED}Error: Required packages not installed${NC}"
    echo "Please install: pip install pandas openai opik python-dotenv openpyxl"
    exit 1
}

# Run the main script
echo -e "${GREEN}Starting LLM processing...${NC}"
echo -e "${GREEN}Output directory: ${OUTPUT_DIR}${NC}"
echo ""

python main.py "$OUTPUT_DIR"

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Processing completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Results saved to:${NC}"
    echo -e "  📁 ${OUTPUT_DIR}/"
    echo -e "  📄 metadata.json"
    echo -e "  📄 output.json"
    echo -e "  📄 results.csv"
    echo ""
    
    # Display summary from output.json if it exists
    if [ -f "$OUTPUT_DIR/output.json" ]; then
        echo -e "${BLUE}Summary:${NC}"
        python -c "
import json
with open('$OUTPUT_DIR/output.json', 'r') as f:
    data = json.load(f)
    print(f\"  Total requests: {data['total_requests']}\")
    print(f\"  Successful: {data['total_success']}\")
    print(f\"  Failed: {data['total_failed']}\")
    print(f\"  Success rate: {data['success_rate']*100:.1f}%\")
    print(f\"  Total runtime: {data['total_runtime_seconds']:.2f}s\")
" 2>/dev/null || echo "  (Summary not available)"
    fi
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Processing failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

