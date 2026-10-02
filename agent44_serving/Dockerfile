# Packages agent44 as a container image. Build from the PROJECT ROOT (the agent imports ../common):
#   docker build -f agent44_serving/Dockerfile -t quiz-agent .
#   docker run --rm -p 8080:8080 quiz-agent
# NOT TESTED in this tutorial (no Docker daemon was running when it was written): treat it as a starting point.
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "google-adk[extensions]>=2.10.0" python-dotenv

# Only the code the agent needs. Secrets (.env) are never copied: see .dockerignore, and pass settings with `docker run -e`.
COPY common ./common
COPY agent44_serving ./agent44_serving

# The container cannot reach "127.0.0.1" on your machine, so the local model is reached through Docker's name for the host.
# Gemini needs Google credentials inside the container (an API key, or a service account); add them with `docker run -e`.
ENV MODEL_PROVIDER=local \
    LOCAL_API_BASE=http://host.docker.internal:1234/v1

EXPOSE 8080
# --host 0.0.0.0 makes the server reachable from outside the container (the default 127.0.0.1 is not).
CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8080", "agent44_serving"]
