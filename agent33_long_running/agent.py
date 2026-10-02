import time

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent33"  # lets AGENT33_MODEL_PROVIDER override the global choice

# Pretend durations in seconds: a video export takes a while, longer for higher quality.
DURATION = {"720p": 20, "1080p": 40, "4k": 90}


# The "ticket" pattern. A slow job must not block the conversation, so the tool only STARTS it and returns an id
# straight away. The job keeps running (here we only pretend, using the clock), and another tool reports its progress.
def start_export(video: str, quality: str, tool_context: ToolContext) -> dict:
    """Starts exporting a video. Returns a job id immediately; the export itself takes a while.

    Args:
        video: The video name, e.g. 'holiday'.
        quality: One of '720p', '1080p' or '4k'.
    """
    quality = quality.strip().lower()
    if quality not in DURATION:
        return {"status": "error", "message": f"quality must be one of {list(DURATION)}"}
    jobs = dict(tool_context.state.get("jobs", {}))
    job_id = f"job-{len(jobs) + 1}"
    jobs[job_id] = {"video": video, "quality": quality, "started": time.time(), "seconds": DURATION[quality]}
    tool_context.state["jobs"] = jobs
    print(f"[job] {job_id} started: {video} in {quality}, takes about {DURATION[quality]} s")
    return {"status": "started", "job_id": job_id, "estimated_seconds": DURATION[quality]}


def check_export(job_id: str, tool_context: ToolContext) -> dict:
    """Reports the progress of an export job.

    Args:
        job_id: The id returned by start_export, e.g. 'job-1'.
    """
    job = tool_context.state.get("jobs", {}).get(job_id)
    if job is None:
        return {"status": "error", "message": f"No job {job_id}"}
    elapsed = time.time() - job["started"]
    percent = min(100, int(100 * elapsed / job["seconds"]))
    print(f"[job] {job_id} checked: {percent}%")
    if percent >= 100:
        return {"status": "done", "job_id": job_id, "file": f"{job['video']}_{job['quality']}.mp4"}
    return {"status": "running", "job_id": job_id, "percent_done": percent,
            "seconds_left": int(job["seconds"] - elapsed)}


def list_jobs(tool_context: ToolContext) -> dict:
    """Lists all export jobs started in this conversation."""
    return {"jobs": sorted(tool_context.state.get("jobs", {}))}


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A video export assistant.",
    instruction=(
        "You help the user export videos. start_export only STARTS an export and returns a job id; tell the user the id and "
        "the estimated time, and that they can keep chatting meanwhile. When they ask about progress, call check_export with "
        "the job id (use list_jobs if you do not know it) and report exactly what it returns. Never say an export is finished "
        "unless check_export returned status 'done'. You can answer other questions while a job runs."
    ),
    tools=[start_export, check_export, list_jobs],
)
