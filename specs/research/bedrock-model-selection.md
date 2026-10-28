# Amazon Bedrock model selection for SME Underwriting Copilot

## Recommendation

Start with Claude Sonnet 5.5 for extraction and, when introduced, risk summaries.
Benchmark Claude Haiku 4.5 on routine extraction before routing production traffic to it.
Use Claude Sonnet 4.6 as an additional comparison baseline.
This is an architectural recommendation based on documented capabilities and observed account availability, not a measured accuracy ranking on this project's financial documents.
Anthropic positions Sonnet 5.5 as its speed/intelligence balance and Haiku models for latency-sensitive extraction and routing.
Both AWS and Anthropic list Sonnet 5.5 and Haiku 4.5; the earlier claim that Haiku 4.5 did not exist was incorrect.
Sources: [Anthropic model overview](https://platform.claude.com/docs/en/about-claude/models/overview), [AWS Sonnet 5.5 card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html), [AWS Haiku 4.5 card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html).

## What was checked

On October 28, 2026, authenticated HTTPS GET requests to the official Bedrock control-plane endpoint in `us-east-1` returned HTTP 200 for `ListFoundationModels`, `ListInferenceProfiles`, and the selected `GetFoundationModelAvailability` calls.
The catalog returned 124 foundation models across 18 providers.
All pages of inference profiles were retrieved, returning 99 profiles.
Catalog membership does not establish permission to invoke a model, so the selected models were also checked individually for authorization, entitlement, agreement, and regional availability.
These are observed API results, interpreted using the [ListFoundationModels API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListFoundationModels.html), [ListInferenceProfiles API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListInferenceProfiles.html), and [GetFoundationModelAvailability API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_GetFoundationModelAvailability.html).

| Candidate | Catalog lifecycle | Authorization | Entitlement | Agreement | Region |
| --- | --- | --- | --- | --- | --- |
| Claude Sonnet 5.5 | ACTIVE | AUTHORIZED | AVAILABLE | AVAILABLE | AVAILABLE |
| Claude Sonnet 4.6 | ACTIVE | AUTHORIZED | AVAILABLE | AVAILABLE | AVAILABLE |
| Claude Haiku 4.5 | ACTIVE | AUTHORIZED | AVAILABLE | AVAILABLE | AVAILABLE |
| Amazon Nova 2 Lite | ACTIVE | AUTHORIZED | AVAILABLE | AVAILABLE | AVAILABLE |
| Claude Sonnet 4.5 | LEGACY | AUTHORIZED | AVAILABLE | AVAILABLE | AVAILABLE |
| Claude Haiku 5.5 | ACTIVE | AUTHORIZED | AVAILABLE | NOT_AVAILABLE | AVAILABLE |
| Claude Opus 5.5 | ACTIVE | AUTHORIZED | AVAILABLE | NOT_AVAILABLE | AVAILABLE |

No model inference, quota change, agreement acceptance, or subscription activation was performed.
Inference success, runtime permissions on profile destination models, quotas, latency, cost per credit file, and extraction quality remain untested.
The `NOT_AVAILABLE` agreement results for Haiku 5.5 and Opus 5.5 are unresolved prerequisites, not evidence that these models are absent from Bedrock.

## Shortlist and intended roles

| Model | Proposed role | Reason and limitation |
| --- | --- | --- |
| Claude Sonnet 5.5 | Initial single-model implementation; complex extraction; fact-grounded summaries | Current Sonnet generation; documented vision and native structured outputs; all selected availability checks passed; financial-document accuracy still needs evaluation. |
| Claude Haiku 4.5 | Routine mapping of clean Docling output into schemas; classification and routing | Documented lightweight speed-oriented model with vision and structured outputs; all selected availability checks passed; do not assume complex tables or faint scans meet accuracy requirements. |
| Claude Sonnet 4.6 | Benchmark comparator or explicitly configured alternative | Vision, native structured outputs, and 1M context documented; all selected availability checks passed; no evidence yet that it beats Sonnet 5.5 for this project. |
| Amazon Nova 2 Lite | Optional document-processing benchmark | AWS describes it as suitable for document processing; available to the checked credentials, but its model card marks native structured outputs unsupported. |
| Claude Haiku 5.5 | Future throughput-focused evaluation candidate | Anthropic targets high-volume extraction; AWS documents structured outputs, but agreement availability did not pass in this account check. |
| Claude Opus 5.5 | Optional demanding-case quality benchmark after access prerequisites are resolved | Documented current model, but agreement availability did not pass; no project-specific evidence justifies making it the default. |

Capability sources: [Sonnet 5.5](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html), [Haiku 4.5](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html), [Sonnet 4.6](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html), [Nova 2 Lite](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-lite.html), [Haiku 5.5](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html), and [Anthropic model overview](https://platform.claude.com/docs/en/about-claude/models/overview).

The broader catalog includes Amazon, Anthropic, OpenAI, Google, Meta, Mistral AI, Qwen, DeepSeek, and other providers.
The shortlist is not a claim that those providers are unsuitable; a full cross-provider benchmark was not run.
The public model catalog is available at [AWS models at a glance](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html).

## Exact inference configuration candidates

Use the `bedrock-runtime` endpoint in `us-east-1` with the Converse API.
The following US system-defined inference profiles were observed as `ACTIVE` in the authenticated profile listing.
The model cards document these profile IDs and API support.

| Model | US inference profile ID |
| --- | --- |
| Sonnet 5.5 | `us.anthropic.claude-sonnet-5-5` |
| Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Sonnet 4.6 | `us.anthropic.claude-sonnet-4-6` |
| Nova 2 Lite | `us.amazon.nova-2-lite-v1:0` |

For these profiles, the observed destination model regions were `us-east-1`, `us-east-2`, and `us-west-2`.
Calling the `us-east-1` endpoint therefore does not mean processing is restricted to that single region.
Prefer an explicitly approved geographic profile over `global.*` when geography matters; even US-only processing needs approval for Philippine merchant data.
Sources: authenticated `ListInferenceProfiles` response, [Sonnet 5.5 regional availability](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html), and [Haiku 4.5 regional availability](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html).

## Extraction design constraints

Keep Docling responsible for parsing and layout, and preserve document/page/table/cell identifiers before sending content to the model.
Ask the model to reference those supplied identifiers instead of inventing source coordinates.
Reject unknown identifiers and missing required evidence through application validation.
Local Docling processing does not make the full pipeline local: the selected document text or images are still sent to Bedrock.
These are proposed controls that implement the source-provenance and deterministic-core requirements in the project's [README](/home/snowaflic/SME-financial/README.md).

Use Bedrock native JSON Schema structured outputs where supported, rather than assuming a request for JSON or a LangChain wrapper guarantees schema compliance.
Converse uses `outputConfig.textFormat`; strict tools are a separate supported mechanism.
Sonnet 5.5 documents only `auto` and `none` tool-choice modes, so do not assume a forced tool-choice strategy used by a wrapper will work unchanged.
Sources: [AWS structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html) and [Sonnet 5.5 model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-5-5.html).

Bedrock supports a subset of JSON Schema, requires `additionalProperties: false` on objects, and does not support numeric constraints such as `minimum`, `maximum`, or `multipleOf` in the constrained schema.
Adapt the generated schema to Bedrock's supported subset, then validate the response again with the full Pydantic model and deterministic business rules.
Native schema compliance cannot establish that amounts, dates, or evidence references are factually correct.
AWS also documents that Anthropic citations and structured outputs cannot be enabled together, so use the application's own provenance IDs instead of relying on that combination.
Haiku 4.5 structured outputs have an India inference-profile exception; the selected profile here is US, not India.
Source: [AWS structured-output schema and feature limitations](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html).

Keep monetary calculations in deterministic Python using decimal-safe representations.
Treat uploaded document text as untrusted data, never as operational instructions.
For summaries, supply validated facts and explicitly flag missing evidence; the model must not invent metrics or make autonomous lending decisions.
These are architectural recommendations, not measured model capabilities.

## Credentials and repository changes

An existing Bedrock bearer token and its configured region were found in another local project with the user's permission.
Only `AWS_BEARER_TOKEN_BEDROCK` and `AWS_REGION` were copied to `/home/snowaflic/SME-financial/.env`.
No unrelated service secrets were copied, and no credential values were printed.
The local file has owner-only `0600` permissions and is excluded by `/home/snowaflic/SME-financial/.gitignore`.
No IAM key pair or shared AWS credentials/config files were found in the inspected locations, so no general AWS account identity or infrastructure permissions are claimed.

AWS documents bearer API keys as an alternative authentication mechanism, recommends short-term keys for production, and limits long-term keys to exploration.
The discovered key's lifetime and IAM policy were not inspected.
Source: [AWS Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html).

The approved constitution was not edited and no Git commit was made for this investigation.

## Evaluation and outstanding decisions

1. Begin with Sonnet 5.5 alone to establish a quality baseline with minimal routing complexity.
2. Compare Haiku 4.5 and Sonnet 4.6 on the same labeled synthetic documents, with a fixed schema and recorded model/profile IDs.
3. Measure exact amount/date extraction, missing and duplicated transactions, provenance validity, balance-check failures, false positives, latency, and total cost per review-ready file.
4. Add anonymized real-world samples only after data-use and retention approval; synthetic accuracy alone does not establish production fitness.
5. Introduce Haiku routing only after it meets the same critical-field accuracy and evidence requirements; failed checks escalate to Sonnet or human review rather than silently accepting a plausible output.
6. Check request/token quotas and current region/profile-specific rates before enabling runtime traffic.

No AWS dollar rates are asserted here because the retrieved AWS pricing page exposed unresolved dynamic price placeholders rather than verified numeric rates for this shortlist.
Anthropic's direct API prices should not be substituted for a confirmed Bedrock regional/profile quote.
Source: [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/).

The decision still needs a paid inference smoke test and an application-specific extraction evaluation.
