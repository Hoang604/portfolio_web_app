### Builder Stage
FROM python:3.12-alpine as builder
WORKDIR /install

# Install build dependencies using apk
RUN apk add --no-cache gcc musl-dev linux-headers build-base

# Copy requirements and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/install/wheels -r requirements.txt

### Final Stage
FROM python:3.12-alpine
WORKDIR /app

# Install runtime dependencies from wheels built in the builder stage
COPY --from=builder /install/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && rm -rf /wheels

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]