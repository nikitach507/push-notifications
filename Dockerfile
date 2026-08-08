# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY main.py ./

# Install dependencies
RUN uv sync --frozen

# Run the bot
CMD ["uv", "run", "python", "main.py"]
