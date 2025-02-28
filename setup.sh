#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Scope Creator Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Python is installed
echo -e "${YELLOW}Checking for Python...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python is not installed. Please install Python 3.6+ and try again.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

# Check if pip is installed
echo -e "${YELLOW}Checking for pip...${NC}"
if ! command -v pip3 &>/dev/null && ! command -v pip &>/dev/null; then
    echo -e "${RED}Error: pip is not installed. Please install pip and try again.${NC}"
    exit 1
fi

if command -v pip3 &>/dev/null; then
    PIP_CMD="pip3"
else
    PIP_CMD="pip"
fi
echo -e "${GREEN}Found pip${NC}"

# Check if venv module is available
echo -e "${YELLOW}Checking for venv module...${NC}"
if ! $PYTHON_CMD -c "import venv" &>/dev/null; then
    echo -e "${RED}Error: venv module not found. Please install it and try again.${NC}"
    echo -e "For Ubuntu/Debian: sudo apt-get install python3-venv${NC}"
    echo -e "For Fedora: sudo dnf install python3-venv${NC}"
    echo -e "For macOS: The venv module should be included with Python${NC}"
    exit 1
fi
echo -e "${GREEN}Found venv module${NC}"

# Check if virtual environment already exists
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Do you want to recreate it? (y/n)${NC}"
    read -r recreate
    if [[ $recreate == "y" || $recreate == "Y" ]]; then
        echo -e "${YELLOW}Removing existing virtual environment...${NC}"
        rm -rf .venv
    else
        echo -e "${GREEN}Using existing virtual environment.${NC}"
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv .venv
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# Determine activation script based on OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    ACTIVATE_SCRIPT=".venv/Scripts/activate"
else
    # Unix-like systems (Linux, macOS)
    ACTIVATE_SCRIPT=".venv/bin/activate"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
if ! source "$ACTIVATE_SCRIPT"; then
    echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
    exit 1
fi
echo -e "${GREEN}Virtual environment activated.${NC}"

# Install requirements
echo -e "${YELLOW}Installing dependencies...${NC}"
if ! $PIP_CMD install -r requirements.txt; then
    echo -e "${RED}Error: Failed to install dependencies.${NC}"
    exit 1
fi
echo -e "${GREEN}Dependencies installed successfully.${NC}"

# Check if .env file exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Found existing .env file. Do you want to update your OpenRouter API key? (y/n)${NC}"
    read -r update_key
    if [[ $update_key == "y" || $update_key == "Y" ]]; then
        echo -e "${YELLOW}Please enter your OpenRouter API key:${NC}"
        read -r api_key
        
        # Update existing .env file
        if grep -q "OPENROUTER_API_KEY=" .env; then
            # Key exists, update it
            sed -i.bak "s/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$api_key/" .env && rm -f .env.bak
        else
            # Key doesn't exist, append it
            echo "OPENROUTER_API_KEY=$api_key" >> .env
        fi
        echo -e "${GREEN}API key updated in .env file.${NC}"
    fi
else
    # Create new .env file
    echo -e "${YELLOW}Please enter your OpenRouter API key:${NC}"
    read -r api_key
    echo "OPENROUTER_API_KEY=$api_key" > .env
    echo -e "${GREEN}.env file created with API key.${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "To run the Scope Creator application:"
echo -e "1. Activate the virtual environment (if not already activated):"
echo -e "   ${YELLOW}source $ACTIVATE_SCRIPT${NC}"
echo -e "2. Start the application:"
echo -e "   ${YELLOW}python app.py${NC}"
echo ""
echo -e "You can access the application in your web browser at:"
echo -e "${BLUE}http://localhost:5006${NC}"
echo ""

# Ask if user wants to run the application now
echo -e "${YELLOW}Do you want to run the application now? (y/n)${NC}"
read -r run_now
if [[ $run_now == "y" || $run_now == "Y" ]]; then
    echo -e "${GREEN}Starting the application...${NC}"
    $PYTHON_CMD app.py
fi 