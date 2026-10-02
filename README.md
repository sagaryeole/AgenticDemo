# Agentic AI with Google ADK, step by step

A hands-on tutorial. Each `agentNN_*` folder adds exactly one new idea to the one before it, and has a
`CASES.md` with a diagram of how it executes plus small cases to try, easiest first.
Concept notes and likely questions are in [questions.md](questions.md).

## The agents

| # | Folder | New idea | Model |
|---|---|---|---|
| 01 | `agent01_poet` | Instruction (system prompt) | Gemini |
| 02 | `agent02_toolcall` | Built-in tool (`google_search`) | Gemini |
| 03 | `agent03_localmodel` | Local model through LiteLLM + LM Studio | local |
| 04 | `agent04_localmodelwithtool` | Your own Python function as a tool | local |
| 05 | `agent05_state` | Session state shared across turns | local |
| 06 | `agent06_structured` | Structured output (`output_schema`) | local |
| 07 | `agent07_multiagent` | Coordinator + specialists (LLM decides) and the global model switch | switchable |
| 08 | `agent08_workflow` | `SequentialAgent`: fixed pipeline | switchable |
| 09 | `agent09_parallel` | `ParallelAgent`: fan out, then fan in | switchable |
| 10 | `agent10_loop` | `LoopAgent`: repeat until good, with a safety cap | switchable |
| 11 | `agent11_guardrails` | Callbacks: block input, validate tool args, edit output | switchable |
| 12 | `agent12_mcp` | Tools from a separate MCP server | switchable |
| 13 | `agent13_evals` | Automated evals with `adk eval` | switchable |
| 14 | `agent14_agent_as_tool` | An agent used as a tool (`AgentTool`), and typed input | switchable |
| 15 | `agent15_confirmation` | Human in the loop: tool confirmation | switchable |
| 16 | `agent16_chunking` | RAG step 1, a lab: cutting a document into chunks | none |
| 17 | `agent17_embeddings` | RAG step 2, a lab: text to vectors | embeddings |
| 18 | `agent18_cosine` | RAG step 3, a lab: cosine similarity and ranking | embeddings |
| 19 | `agent19_retrieval` | RAG step 4, a lab: top-k, minimum score, hybrid search | embeddings |
| 20 | `agent20_rag` | RAG agent that answers only from a document, with an eval | switchable |
| 21 | `agent21_memory` | Long-term memory: a file-backed agent and ADK's `MemoryService` | switchable |
| 22 | `agent22_code_execution` | Exact answers: Gemini code execution, or safe calculator tools | switchable |
| 23 | `agent23_artifacts` | Saving versioned files (artifacts) | switchable |
| 24 | `agent24_planning` | Thinking and planners, measured on puzzles | Gemini / switchable |
| 25 | `agent25_multiturn_evals` | Evaluating multi-turn conversations | switchable |
| 26 | `agent26_observability` | Plugins, logs and OpenTelemetry spans | switchable |
| 27 | `agent27_a2a` | Agent-to-Agent (A2A): calling an agent in another process | switchable |

Notes on this table:
- "switchable" means the model comes from `MODEL_PROVIDER` (see Setup). "embeddings" means it uses `EMBEDDING_PROVIDER` instead.
- Agents 16-19 are **labs**: plain Python scripts you run with `uv run python agentNN_.../script.py`, not agents you chat with.
  Their `CASES.md` says exactly what to run.
- Agents 21 and 24 have extra scripts next to `agent.py`. Agent 27 needs two terminals.
- Agents 16-20 share `data/handbook.md` and the code in `common/rag.py` and `common/embeddings.py`.
- `triage_agent` is a separate, earlier experiment (RAG over runbooks) and is not part of the sequence.

## Setup

1. Install [uv](https://docs.astral.sh/uv/). It installs the right Python and all packages for you.
2. Install dependencies:

       uv sync

3. Create your config from the example and fill in your project id:

       cp .env.example .env

   One `.env` in the project root is enough. ADK looks for `.env` in the agent's folder and then in each
   parent folder, so every agent finds this one. `.env` is git-ignored.
4. For Gemini (agents 01-02, and 07+ with `MODEL_PROVIDER=gemini`), set up Google Cloud once:

       gcloud auth login
       gcloud auth application-default login
       gcloud auth application-default set-quota-project YOUR_PROJECT_ID
       gcloud config set project YOUR_PROJECT_ID
       gcloud services enable aiplatform.googleapis.com

5. For a local model (agents 03-06, and 07+ with `MODEL_PROVIDER=local`): install
   [LM Studio](https://lmstudio.ai/), load a model, and start the server in the Developer tab.
   Set `LOCAL_MODEL_ID` in `.env` to the id shown by `curl http://127.0.0.1:1234/v1/models`.
6. For the RAG labs and agent 20, embeddings come from `EMBEDDING_PROVIDER`: `gemini` (default, uses the Google setup above) or
   `local` (an embedding model loaded in LM Studio, `text-embedding-embeddinggemma-300m` by default). These variables are optional
   and not in `.env.example`: `EMBEDDING_PROVIDER`, `GEMINI_EMBEDDING_MODEL`, `LOCAL_EMBEDDING_MODEL`.

If you see `No API key was provided`, the Gemini settings in `.env` are missing.
Gemini can answer `429 RESOURCE_EXHAUSTED` when many calls arrive quickly (long evaluation loops). Wait a minute and retry.

## Run

    uv run adk run agent07_multiagent      # chat in the terminal
    uv run adk web                         # browser UI with traces and session state

Switch the model for agents 07+ without editing code:

    MODEL_PROVIDER=local  uv run adk run agent08_workflow
    MODEL_PROVIDER=gemini uv run adk run agent08_workflow

Run the evals (agents 13, 20 and 25):

    uv run adk eval agent13_evals agent13_evals/bookshop.evalset.json \
        --config_file_path agent13_evals/test_config.json
