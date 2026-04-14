# GlitchHunter Sandbox -- Isolated test execution environment
# Network-disabled, timeout-enforced container for safe patch testing

FROM python:3.11-slim

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install test frameworks for all supported languages
RUN pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-asyncio>=0.23.3 \
    pytest-cov>=4.1.0 \
    hypothesis>=6.97.0 \
    pytest-timeout>=2.2.0

WORKDIR /sandbox

# Copy test runner script
COPY test_runner.sh /sandbox/test_runner.sh
RUN chmod +x /sandbox/test_runner.sh

# Default: run tests with timeout
ENTRYPOINT ["/sandbox/test_runner.sh"]
CMD ["--timeout", "60"]
