# Agentic AI with Google ADK, step by step

A hands-on tutorial. Each `agentNN_*` folder adds exactly one new idea to the one before it, and has a
`CASES.md` with a diagram of how it executes plus small cases to try, easiest first. The last one, agent50,
is a capstone that combines the main ideas in one agent.
[questions.md](questions.md) is the study guide: 12 topic modules with diagrams, charts of the measured results, the main lessons,
and 100 questions (with hidden answers) to check your understanding.

![adk web showing agent07: the coordinator hands off to the weather agent, which calls its tool; the Traces tab shows the timing](docs/adk-web-trace.gif)

*`uv run adk web` on agent07: the hand-off, the tool call, and the timing of each step (a local model through LM Studio).*

## Learning tracks

New to ADK? Go in order. Looking for one topic? Pick a track. Each link opens that agent's `CASES.md`.

### 🟢 Core fundamentals

Instructions, tools, local models, state, structured output, memory, code execution, images and prompt building.

[01](agent01_poet/CASES.md) · [02](agent02_toolcall/CASES.md) · [03](agent03_localmodel/CASES.md) · [04](agent04_localmodelwithtool/CASES.md) · [05](agent05_state/CASES.md) · [06](agent06_structured/CASES.md) · [21](agent21_memory/CASES.md) · [22](agent22_code_execution/CASES.md) · [23](agent23_artifacts/CASES.md) · [28](agent28_multimodal/CASES.md) · [29](agent29_dynamic_instructions/CASES.md) · [30](agent30_long_conversations/CASES.md) · [45](agent45_data_analyst/CASES.md)

### 🟡 Orchestration & workflows

Several agents working together: coordinators, pipelines, loops, graphs, A2A, planning and long jobs.

[07](agent07_multiagent/CASES.md) · [08](agent08_workflow/CASES.md) · [09](agent09_parallel/CASES.md) · [10](agent10_loop/CASES.md) · [14](agent14_agent_as_tool/CASES.md) · [24](agent24_planning/CASES.md) · [27](agent27_a2a/CASES.md) · [33](agent33_long_running/CASES.md) · [42](agent42_supervisor_critic/CASES.md) · [46](agent46_graph_workflow/CASES.md) · [47](agent47_batch_processing/CASES.md)

### 🔵 RAG & search

Chunking, embeddings, similarity, retrieval, hybrid search and reranking, and how to measure a RAG pipeline.

[16](agent16_chunking/CASES.md) · [17](agent17_embeddings/CASES.md) · [18](agent18_cosine/CASES.md) · [19](agent19_retrieval/CASES.md) · [20](agent20_rag/CASES.md) · [35](agent35_hybrid_rerank/CASES.md) · [36](agent36_rag_eval/CASES.md) · [37](agent37_fewshot_selection/CASES.md)

### 🔴 Tools, evals, safety & production

Guardrails, MCP and OpenAPI tools, evals, observability, security, cost, resilience, serving, and the capstone.

[11](agent11_guardrails/CASES.md) · [12](agent12_mcp/CASES.md) · [13](agent13_evals/CASES.md) · [15](agent15_confirmation/CASES.md) · [25](agent25_multiturn_evals/CASES.md) · [26](agent26_observability/CASES.md) · [31](agent31_prompt_injection/CASES.md) · [32](agent32_openapi_tools/CASES.md) · [34](agent34_persistent_sessions/CASES.md) · [38](agent38_many_tools/CASES.md) · [39](agent39_cost_speed/CASES.md) · [40](agent40_fallback_timeouts/CASES.md) · [41](agent41_tool_auth/CASES.md) · [43](agent43_streaming/CASES.md) · [44](agent44_serving/CASES.md) · [48](agent48_permissions/CASES.md) · [49](agent49_distillation/CASES.md) · [50](agent50_capstone/CASES.md)

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
| 28 | `agent28_multimodal` | Images as input (both models read images) | switchable |
| 29 | `agent29_dynamic_instructions` | An instruction built from state on every call, and few-shot examples | switchable |
| 30 | `agent30_long_conversations` | Long chats: keep everything, trim, or summarise | switchable |
| 31 | `agent31_prompt_injection` | Hidden instructions in data, and layered defences | switchable |
| 32 | `agent32_openapi_tools` | Tools generated from a REST API's OpenAPI description | switchable |
| 33 | `agent33_long_running` | Slow jobs: the ticket pattern, and pause-and-resume | switchable |
| 34 | `agent34_persistent_sessions` | Sessions in a database, and state scopes (`user:`) | switchable |
| 35 | `agent35_hybrid_rerank` | A lab: vector search, keyword search (BM25), hybrid fusion, and an LLM reranker | switchable |
| 36 | `agent36_rag_eval` | A lab: measuring a whole RAG pipeline, retrieval and answer separately | switchable |
| 37 | `agent37_fewshot_selection` | Showing the model the most similar examples, picked with embeddings | switchable |
| 38 | `agent38_many_tools` | 20 tools: descriptions, token cost, and routing to the few that fit | switchable |
| 39 | `agent39_cost_speed` | A lab: tokens and seconds, model sizes, a router, output caps, context caching | Gemini / switchable |
| 40 | `agent40_fallback_timeouts` | A backup model, time limits and a circuit breaker | switchable |
| 41 | `agent41_tool_auth` | Giving a tool its secret token without the model seeing it | switchable |
| 42 | `agent42_supervisor_critic` | A supervisor managing a planner, a writer and a fact checker | switchable |
| 43 | `agent43_streaming` | Showing the reply while it is written (SSE streaming) | switchable |
| 44 | `agent44_serving` | An agent behind an HTTP API (`adk api_server`), a client, and a Dockerfile | switchable |
| 45 | `agent45_data_analyst` | Questions about a table: pandas tools, Gemini code execution, or no help, measured | switchable |
| 46 | `agent46_graph_workflow` | A workflow drawn as a graph: nodes, routes, a branch without a model, and retries | switchable |
| 47 | `agent47_batch_processing` | One agent over many items: concurrency, retries, saved results and resume | switchable |
| 48 | `agent48_permissions` | Who may do what: a role check in code against a prompt-only rule, and a rate limit | switchable |
| 49 | `agent49_distillation` | A lab: a big model labels examples, a small model uses them | Gemini + local |
| 50 | `agent50_capstone` | **Capstone**: a library assistant that combines search, bookings with approval, permissions, memory, injection defences, a backup model, tests and an HTTP client | switchable |

Notes on this table:
- "switchable" means the model comes from `MODEL_PROVIDER` (see Setup). "embeddings" means it uses `EMBEDDING_PROVIDER` instead.
- Agents 16-19, 35, 36, 39 and 49 are **labs**: plain Python scripts you run with `uv run python agentNN_.../script.py`, not agents you chat with.
  Their `CASES.md` says exactly what to run. (Labs 35, 36, 39 and 49 call a model directly through `common/llm.py`.)
- Several agents have extra files next to `agent.py`: tests and demos (21, 24, 26, 28, 30, 31, 33, 34, 37, 38, 43, 45-48, 50),
  small servers (12, 27, 32, 41) and HTTP clients (44, 50). Their `CASES.md` says how to run them.
  Agents 27, 32, 41, 44 and 50 (its HTTP client) need two terminals: one for a server, one for the agent or client.
- Agents 16-20, 35, 36 and 50 share `data/handbook.md` and the code in `common/rag.py` and `common/embeddings.py`.

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
6. For the RAG labs, agent 20, agents 35-38, 49 and 50, embeddings come from `EMBEDDING_PROVIDER`: `gemini` (default, uses the Google setup above) or
   `local` (an embedding model loaded in LM Studio, `text-embedding-embeddinggemma-300m` by default). These variables are optional
   and not in `.env.example`: `EMBEDDING_PROVIDER`, `GEMINI_EMBEDDING_MODEL`, `LOCAL_EMBEDDING_MODEL`.

If you see `No API key was provided`, the Gemini settings in `.env` are missing.
Gemini can answer `429 RESOURCE_EXHAUSTED` when many calls arrive quickly. Agents 07+ retry automatically (see `common/models.py`);
if it still fails, wait a minute and try again.

## Run

    uv run adk run agent07_multiagent      # chat in the terminal
    uv run adk web                         # browser UI with traces and session state

Switch the model for agents 07+ without editing code:

    MODEL_PROVIDER=local  uv run adk run agent08_workflow
    MODEL_PROVIDER=gemini uv run adk run agent08_workflow

Run the evals (agents 13, 20, 25 and 50):

    uv run adk eval agent13_evals agent13_evals/bookshop.evalset.json \
        --config_file_path agent13_evals/test_config.json
    uv run adk eval agent20_rag agent20_rag/rag.evalset.json \
        --config_file_path agent20_rag/rag_config.json
    uv run adk eval agent25_multiturn_evals agent25_multiturn_evals/lunch.evalset.json \
        --config_file_path agent25_multiturn_evals/multiturn_config.json
    uv run adk eval agent50_capstone agent50_capstone/library.evalset.json \
        --config_file_path agent50_capstone/eval_config.json

## How to study

1. Go through the agents in order. Each `CASES.md` starts with a diagram, then cases from easy to hard.
2. Run each case yourself, compare with the "Expect" line, then read "Learn".
3. Results that involve a language model can differ between runs and between Gemini and the local model.
   The "Expect" lines say what happened when the case was tested.
4. After each group of agents, read the matching module of the study guide [questions.md](questions.md) and answer its questions.
