
# Day 1:  
## Enable GCP 

    gcloud auth login
    gcloud auth application-default login
    gcloud auth application-default set-quota-project YOUR_PROJECT_ID
    gcloud config set project YOUR_PROJECT_ID
    gcloud services enable aiplatform.googleapis.com logging.googleapis.com cloudtrace.googleapis.com monitoring.googleapis.com

## Initialize project and install ADK

    uv init aiops-poc && cd aiops-poc
    uv add google-adk
    mkdir triage_agent

## Run Command
    uv run adk web.                 // for Web
    uv run adk run triage_agent     // for cmdline