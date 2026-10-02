"""Print every finished OpenTelemetry span on one line.

ADK creates spans (timed records with a name and attributes) for each agent run, model call and tool call, using the
OpenTelemetry API. By default nothing receives them. Production setups send them to Cloud Trace or another backend with an
exporter. Here a tiny exporter simply prints them, which shows the same structure without any cloud setup.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult


class OneLineExporter(SpanExporter):
    def export(self, spans):
        for span in spans:
            ms = (span.end_time - span.start_time) / 1e6
            keep = {k: v for k, v in (span.attributes or {}).items() if k in ("gen_ai.operation.name", "gen_ai.tool.name", "gen_ai.agent.name", "gen_ai.request.model")}
            print(f"[span] {ms:8.1f} ms  {span.name:<32} {keep}")
        return SpanExportResult.SUCCESS


def enable_span_printing() -> None:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(OneLineExporter()))
    trace.set_tracer_provider(provider)
