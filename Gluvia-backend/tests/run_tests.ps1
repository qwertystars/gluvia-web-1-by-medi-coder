# run_tests.ps1
# PowerShell script to run all tests for Gluvia project
# Run from the project root directory

Write-Host "Starting Gluvia Test Suite..." -ForegroundColor Green

# Install/upgrade dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables for testing
$env:TESTING = "true"
$env:TEST_DATABASE_URL = "sqlite:///./test_gluvia.db"

# Create logs directory if it doesn't exist
if (!(Test-Path "logs"))
{
    New-Item -ItemType Directory -Path "logs"
}

# Run tests with coverage
Write-Host "Running tests with coverage..." -ForegroundColor Cyan
pytest tests/ -v --cov=. --cov-report=html:tests/htmlcov --cov-report=json:tests/test_results.json --cov-report=term-missing --tb=short

# Check results
if ($LASTEXITCODE -eq 0)
{
    Write-Host "All tests passed successfully!" -ForegroundColor Green
    Write-Host "Coverage report generated in tests/htmlcov/index.html" -ForegroundColor Blue
}
else
{
    Write-Host "Some tests failed. Check the output above for details." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Clean up test database
if (Test-Path "test_gluvia.db")
{
    Remove-Item "test_gluvia.db" -Force
    Write-Host "Cleaned up test database" -ForegroundColor Yellow
}

Write-Host "Test suite completed!" -ForegroundColor Green
