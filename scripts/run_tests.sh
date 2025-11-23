#!/bin/bash
# Script to run LazyGradle tests with various options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    echo "LazyGradle Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  all              Run all tests (default)"
    echo "  unit             Run unit tests only"
    echo "  ui               Run UI tests only"
    echo "  integration      Run integration tests only"
    echo "  coverage         Run tests with coverage report"
    echo "  fast             Run tests excluding slow tests"
    echo "  watch            Run tests in watch mode (requires pytest-watch)"
    echo "  help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit          # Run unit tests"
    echo "  $0 coverage      # Run all tests with coverage"
    echo "  $0 fast          # Run fast tests only"
}

run_all_tests() {
    echo -e "${GREEN}Running all tests...${NC}"
    pytest -v
}

run_unit_tests() {
    echo -e "${GREEN}Running unit tests...${NC}"
    pytest -v -m unit
}

run_ui_tests() {
    echo -e "${GREEN}Running UI tests...${NC}"
    pytest -v -m ui
}

run_integration_tests() {
    echo -e "${GREEN}Running integration tests...${NC}"
    pytest -v -m integration
}

run_with_coverage() {
    echo -e "${GREEN}Running tests with coverage...${NC}"
    pytest --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml
    echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
}

run_fast_tests() {
    echo -e "${GREEN}Running fast tests (excluding slow tests)...${NC}"
    pytest -v -m "not slow"
}

run_watch_mode() {
    echo -e "${GREEN}Running tests in watch mode...${NC}"
    if ! command -v ptw &> /dev/null; then
        echo -e "${RED}pytest-watch not found. Install with: pip install pytest-watch${NC}"
        exit 1
    fi
    ptw -- -v
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Not in the LazyGradle root directory${NC}"
    echo "Please run this script from the project root"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Install test dependencies with: pip install -r requirements-dev.txt"
    exit 1
fi

# Parse command line arguments
case "${1:-all}" in
    all)
        run_all_tests
        ;;
    unit)
        run_unit_tests
        ;;
    ui)
        run_ui_tests
        ;;
    integration)
        run_integration_tests
        ;;
    coverage)
        run_with_coverage
        ;;
    fast)
        run_fast_tests
        ;;
    watch)
        run_watch_mode
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac
