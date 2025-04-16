# Use the Python 3.12-slim for a smaller image that is compatable with scikit-learn & scikit-surprise
# https://hub.docker.com/_/python
FROM python:3.12-slim


# Install build dependencies
# Below are the dependency setups to used scikit-surprise which is a Cython-based package (I compile C extensions)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*


# Create and change to the `/home/ecom-recommendation-backend` directory.
WORKDIR /ecom-recommendation-backend

# Copy local code to the container image.
COPY . .

# Install upgrade pip and install project dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
# RUN pip install -r requirements.txt

EXPOSE 8000

# Run the web service on container startup.
# CMD ["fastapi", "run", "--workers", "4", "app/main.py"]

CMD ["uvicorn", "app.main:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]