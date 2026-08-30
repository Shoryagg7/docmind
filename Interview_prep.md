# DocMind — Interview Prep

Deep conceptual explanations, written so Shorya can defend every design decision in an interview without looking anything up. Updated at the end of each completed phase. Sections are numbered contiguously and never renumbered.

---

## 1. Embeddings

**What it is**
An embedding is a fixed-length vector of floating-point numbers that represents the *meaning* of a piece of text. A sentence-embedding model maps any input text to a point in a high-dimensional space (384 dimensions for `all-MiniLM-L6-v2`) such that texts with similar meaning land close together, and texts with different meaning land far apart. The model is trained so that geometric closeness in vector space approximates semantic closeness in meaning — that's what lets a query like "what did the contract say about termination" retrieve a chunk saying "either party may end this agreement with 30 days notice," even though the two share almost no words.

**Why we chose it**
Requirement: DocMind must find document chunks relevant to a natural-language question without relying on exact keyword overlap.
Choice: `sentence-transformers` with `all-MiniLM-L6-v2` to embed both chunks and queries into 384-dim vectors.
Benefit: small (~80MB), fast on CPU, no per-call cost, no network dependency, and well-benchmarked — easy to defend in an interview.
Cost: lower retrieval ceiling than larger models (OpenAI `text-embedding-3-large`, BGE-large); fixed 384 dims caps how much fine-grained distinction it can represent in a dense technical corpus.
Rejected alternative: a hosted embedding API (OpenAI/Cohere) — rejected because it adds per-call cost, network latency, and an external dependency for a project scoped to run locally via Docker Compose; a local, deterministic, offline model is also easier to reason about while learning.

**Soundbite**
"An embedding turns text into a vector — a list of numbers placed in space so that meaning becomes geometry. Two chunks that mean similar things land close together, so instead of matching keywords I'm matching meaning. I used `all-MiniLM-L6-v2` because it's small, runs on CPU, costs nothing per call, and is good enough for a document corpus this size — I didn't need OpenAI's embedding API for a portfolio project."

**The gotcha**
Embeddings capture semantic *similarity*, not logical or factual correctness — that's why negation is a classic failure mode. "The drug is approved for adults" and "the drug is NOT approved for adults" embed very close together because they share almost every word and the same topic, even though they mean opposite things. This is exactly why DocMind has a dedicated negation test set in Phase 9 — cosine similarity alone can't tell you the two sentences disagree.

**Self-test**
- Why do "cat" and "kitten" end up close together in embedding space, but "cat" and "cot" (similar spelling, unrelated meaning) do not?
- What does it concretely mean for an embedding model to have "384 dimensions"?
- Why can't you directly compare embeddings produced by two different models (e.g., MiniLM vs. an OpenAI embedding model)?
- Why does negation break naive embedding similarity, and what would you need to add to catch it?
- If you doubled the chunk size, would you expect embedding quality to go up, down, or depend on something else? Why?

---

## 2. Cosine Similarity (vs. Euclidean Distance)

**What it is**
Cosine similarity measures the *angle* between two vectors, ignoring their magnitude — it answers "do these two vectors point in the same direction," not "how far apart are their endpoints." It's the dot product of two vectors divided by the product of their magnitudes, ranging from -1 (opposite direction) to 1 (identical direction), with 0 meaning unrelated/orthogonal. Euclidean distance instead measures straight-line distance between the two points, which is sensitive to vector length as well as direction.

**Why we chose it**
Requirement: rank document chunks by how relevant they are to a query embedding.
Choice: cosine similarity as the distance metric for top-k retrieval.
Benefit: sentence-transformer embeddings are trained so that *direction* carries the semantic signal, not magnitude — two paraphrases of the same idea can have different vector lengths but should still count as "the same." Cosine is also the standard metric these models are benchmarked against, and what pgvector's operators are built around.
Cost: discards magnitude information entirely; not a true metric (doesn't satisfy the triangle inequality the way Euclidean does), which matters if a future feature ever needed metric-space guarantees.
Rejected alternative: Euclidean (L2) distance — rejected because it conflates "different length" with "different meaning" and is more sensitive to magnitude drift between embeddings; cosine is the standard fit for sentence-transformer output.

**Soundbite**
"To rank chunks I need a number that says 'how similar are these two vectors.' Cosine similarity looks at the angle between them, not the distance, so two vectors pointing the same direction score as similar even if one is longer. Sentence-transformer embeddings are trained so direction carries the meaning, so cosine is the natural fit — and it's what pgvector uses under the hood."

**The gotcha**
Cosine similarity assumes a well-normalized embedding space — mix embeddings from two different models, or forget to normalize, and similarity scores stop being comparable across queries. It's also easy to misuse pgvector's `<=>` operator, which returns *cosine distance* (`1 - cosine similarity`), not similarity — so smaller is better, the opposite of what "similarity" intuitively suggests. A bug here silently inverts your ranking instead of crashing, which makes it a nasty one to catch.

**Self-test**
- Why does cosine similarity ignore vector magnitude, and when would that be the wrong choice?
- What's the mathematical relationship between cosine similarity and cosine distance? Which one does pgvector's `<=>` operator return?
- If two chunks score a cosine similarity of 0.95, what does that actually tell you about their meaning — and what does it *not* tell you?
- Why might Euclidean distance and cosine similarity disagree about which of two chunks is "more similar" to a query?
- How would you pick a similarity threshold for "this chunk isn't relevant enough to use"? What can go wrong with a fixed threshold?

---

## 3. Chunking and Overlap

**What it is**
Chunking is splitting a document into smaller pieces before embedding and storing them, because you can't (and shouldn't) embed or retrieve an entire document as one unit — an embedding model compresses text into a single fixed-size vector, and the more text you cram in, the more that vector becomes an average of many unrelated ideas, diluting the very signal retrieval depends on. DocMind's chunker (`services/chunker.py`) uses a fixed-size sliding window: take `chunk_size` characters, then slide forward by `chunk_size - overlap` (not the full `chunk_size`), so consecutive chunks share a trailing/leading region of text. That shared region — the overlap — exists purely to stop a sentence or clause that happens to fall across a chunk boundary from being truncated in both of the chunks it lands in.

**Why we chose it**
Requirement: split extracted PDF text into pieces small enough to embed meaningfully, without losing information that straddles a split point.
Choice: character-based fixed-size chunking with a configurable overlap (defaults: 500 chars, 50 overlap).
Benefit: dead simple to implement and reason about, no extra dependency, and its failure modes (a phrase split across a boundary) are easy to demonstrate and understand before reaching for something fancier.
Cost: character count isn't the same as token count (the unit the embedding model and LLM actually operate on), and it ignores document structure entirely — it will just as happily cut a chunk boundary in the middle of a sentence, a table row, or a heading as anywhere else.
Rejected alternative: sentence- or paragraph-aware chunking (e.g., via `nltk`/`spaCy` sentence tokenization, or LangChain's `RecursiveCharacterTextSplitter`). Rejected for now because it hides the underlying mechanism behind an abstraction before the naive version's behavior — and its failure modes — have actually been observed; it's a legitimate upgrade to revisit once the naive baseline's limitations are felt, not before.

**Soundbite**
"An embedding model needs bite-sized input, so I split each document into overlapping chunks before embedding them — fixed size, with a sliding window so consecutive chunks share some text. The overlap exists so a sentence that happens to fall on a chunk boundary doesn't get truncated in both halves and lose its meaning in each. I kept it character-based and structure-blind on purpose for the first pass — it's the simplest version, and its failure modes are exactly what motivate smarter chunking strategies later."

**The gotcha**
Chunk size and overlap are a trade-off, not a free parameter to maximize: too small and each chunk lacks enough surrounding context to be individually meaningful, hurting both its embedding quality and how useful it is once retrieved; too large and the chunk's embedding gets diluted by unrelated content in the same chunk, hurting retrieval precision, while also wasting LLM context window at generation time. There's no universally correct size — it depends on document type and the kind of questions being asked. A second gotcha: overlap increases storage and embedding cost roughly linearly (each token of overlap gets embedded twice, once per chunk it appears in), so it's not free to just crank overlap up to be safe.

**Self-test**
- Why can't you just embed an entire document as a single vector instead of chunking it?
- What does the `overlap` parameter actually buy you, mechanically, in a sliding-window chunker?
- Why is character-based chunk size not the same thing as token-based chunk size, and why does that matter once you plug in an actual embedding model?
- If a document is mostly short, single-sentence bullet points, would you want a larger or smaller chunk size than for a document of dense legal prose? Why?
- What's a concrete failure case where fixed-size chunking without overlap would return a chunk that's individually useless, even though the source document clearly contains the answer?

---

## 4. Vector Indexes: Exact Search vs. HNSW (Approximate Nearest Neighbor)

**What it is**
Top-k retrieval means: given a query embedding, find the k stored chunk embeddings closest to it. The direct way to do this — exact search — computes the distance between the query and *every single row*, sorts, and returns the top k. It's correct by construction (there's no approximation anywhere), but it's O(n) per query: double the rows, double the work. HNSW (Hierarchical Navigable Small World) is an *index* that trades a small amount of correctness for speed at scale: it pre-builds a graph structure over the stored vectors at insert time, so a query can navigate straight toward the neighborhood of likely-closest vectors instead of touching every row — sub-linear query time, but it can occasionally miss the true nearest neighbor in exchange for that speed, which is why it's called *approximate* nearest neighbor (ANN) search.

**Why we chose it**
Requirement: retrieve the top-k most relevant chunks for a query, correctly, and understand when an index actually helps versus when it's dead weight.
Choice: build and observe both — exact search first (Unit 8), then add an HNSW index and directly compare query plans (Unit 9), rather than picking one and only reading about the other.
Benefit: this isn't theoretical — `EXPLAIN ANALYZE` showed Postgres's query planner make its own cost-based decision: at 3 rows it used `Seq Scan` and ignored the HNSW index entirely (correct — index overhead isn't worth it at that size); at 3003 rows (3000 synthetic vectors added temporarily) it switched to `Index Scan using chunks_embedding_hnsw_idx` on its own, no query change required. Watching the planner flip its own decision at scale is a much stronger interview answer than reciting "HNSW is faster."
Cost: HNSW is approximate — at extreme scale or with poorly tuned parameters it can miss true nearest neighbors, and it costs more to build/update than a plain B-tree; also needs the right operator class (`vector_cosine_ops`) matching the distance function actually used in queries, or the index silently can't be used at all.
Rejected alternative (for now): IVFFlat, pgvector's other index type. Rejected because it requires the table to already have representative data before building (it clusters existing vectors into centroids at build time), which is an awkward fit for an ingestion pipeline where documents arrive incrementally — HNSW supports incremental inserts naturally. Worth knowing IVFFlat exists and why it wasn't the pick, not worth building both.

**Soundbite**
"Exact search checks every row, so it's always correct but scales linearly — fine for hundreds of chunks, not for millions. HNSW builds a navigable graph over the vectors so a query can jump straight to the right neighborhood instead of scanning everything, trading a small amount of recall for speed. I didn't just take that on faith — I built the index, ran `EXPLAIN ANALYZE` at 3 rows and at 3000+ rows, and watched Postgres's own planner ignore the index at small scale and switch to using it once there was enough data to make it worth the overhead."

**The gotcha**
The single most dangerous failure mode I hit in this whole phase wasn't the index — it was `ORDER BY embedding <=> :query DESC` instead of `ASC`. pgvector's `<=>` operator returns *distance* (lower = more similar), so ordering descending doesn't error, doesn't warn, doesn't crash — it just silently returns the *least* relevant results first, and everything downstream (citations, generated answers) would confidently be wrong with no signal that anything broke. A second, subtler gotcha: an HNSW index built with the wrong operator class (say, `vector_l2_ops` when your queries use cosine distance) won't be used by the query planner at all — no error, the query just quietly falls back to a sequential scan, and you'd only notice by checking the query plan.

**Self-test**
- Why is exact nearest-neighbor search O(n) per query, and what specifically about HNSW's structure avoids touching every row?
- Why did Postgres's query planner choose *not* to use the HNSW index at 3 rows, even though the index existed?
- What does pgvector's `<=>` operator actually return, and what happens — silently — if you sort by it in the wrong direction?
- Why does an HNSW index need its operator class (e.g. `vector_cosine_ops`) to match the distance function used in the query, and what happens if they don't match?
- At what point (roughly, and why) would you expect exact search to become a real bottleneck for DocMind, given the corpus sizes a portfolio project actually deals with?

---

## 5. Top-k Retrieval: Choosing k, and Filtered Vector Search

**What it is**
`k` is how many chunks a single retrieval call asks for — and it's a real trade-off dial, not a "bigger is safer" setting. It was proven directly, not just argued: with `k=3`, a query asking to list all projects on a resume returned only one, because the second project's chunk simply didn't rank in the top 3 — a **recall failure** (the right information existed in the corpus but never reached the LLM). Raising `k` to 6 fixed that, but the response then returned all 6 retrieved chunks as "sources" — most of them irrelevant (skills, extracurriculars) — a **precision problem** (too much noise reaching the LLM and the client). Those are two different failure modes, fixed two different ways: recall by raising `k`, precision by filtering the returned `sources` down to only the chunks the LLM actually cited in its answer. Raising `k` doesn't fix precision, and filtering citations doesn't fix recall — each needed its own fix.

Separately, `search()` gained an optional equality filter: `WHERE source = :source`, combined in the same query with the existing `ORDER BY embedding <=> :query` ranking. This is document/metadata scoping — restricting the vector search to rows matching an exact structured condition before or alongside ranking by similarity. It's a very common real RAG pattern (often called "filtered vector search"), and it's exactly what stops one uploaded document's chunks from silently competing with another's for the same top-k slots.

**Why we chose it**
Requirement: answer "list all X" questions completely; keep citations honest (only show what was actually used); let a query be restricted to one uploaded document instead of the whole corpus.
Choice: keep `k` as a per-query parameter (not hardcoded), default modest but overridable; filter `sources` post-generation to only cited chunk IDs; add an optional `source` equality filter alongside the existing similarity ordering.
Benefit: each of the three real failures this project actually hit — missed enumeration, noisy citations, cross-document contamination — got fixed by its own small, targeted change, each provably working (verified with real multi-document uploads, not just unit tests).
Cost: `k` is still a blunt instrument — raising it is not a real fix for enumeration at real scale (a corpus with hundreds of chunks and dozens of "project"-like items would need a fundamentally different retrieval strategy, not `k=50`). Document scoping requires the caller to already know the exact `source` string — no fuzzy matching, no automatic per-session isolation; get the string wrong and you silently search nothing (or everything, if omitted) rather than getting an error.

**Soundbite**
"`k` isn't a safety knob you just turn up — I hit both failure modes myself. `k=3` missed a second project because its chunk didn't rank in the top 3: a recall problem. Raising it to `k=6` fixed that but returned four irrelevant chunks as sources until I filtered citations down to only what the model actually referenced: a precision problem, fixed separately. Then I added document scoping — a plain equality filter on `source`, combined with the existing vector similarity ordering in the same query — because without it, two uploaded documents' chunks competed for the same slots, and I watched that produce a genuinely correct 'I don't know' when I asked an ambiguous question with both documents live."

**The gotcha**
Two indexes are doing two completely different jobs here, and conflating them is an easy interview slip. The B-tree index (`chunks_source_idx`) is built on the `source` column and answers "which rows exactly equal this value" — the ordinary, default index type for equality/range filtering, same job it does for a primary key. The HNSW index (`chunks_embedding_hnsw_idx`) is built on the `embedding` column and answers a completely different question — "which rows are approximately closest to this vector" — needing a graph structure, not a sorted tree. A single query can use both together (B-tree filters down to one document's rows, HNSW ranks the filtered set by similarity), but neither index can do the other's job, and mixing up "which key backs which index" is exactly the kind of detail an interviewer will probe.

**Self-test**
- Why does raising `k` fix a missed-item recall problem but not fix it "for real" at a much larger corpus size?
- What's the practical difference between a recall problem and a precision problem in retrieval — and which one did each of DocMind's two real failures actually correspond to?
- What column is the B-tree index built on, and what column is the HNSW index built on? Why can't either substitute for the other?
- Why doesn't filtering the `sources` field change how many chunks were retrieved or how many tokens the LLM call cost?
- If a corpus had 10 documents with 50 chunks each, what would have to change about the current retrieval design to reliably answer "list every project across all my documents" — is raising `k` a real answer here, and why or why not?

---

## 6. Grounding and Citations via Prompt Construction

**What it is**
Grounding means constraining an LLM's answer to only use information that was actually retrieved and handed to it in the prompt, instead of freely drawing on whatever it memorized during pretraining. There's no special API flag for this — it's done by instruction: the system prompt explicitly tells the model "answer only from the provided context; if the context doesn't contain the answer, say you don't know," and the retrieved chunks are pasted into the prompt, numbered, so the model can reference them. Citations are the model tagging each claim with which numbered chunk it came from (`[1]`, `[2]`), so a reader can trace an answer back to its source instead of trusting it blindly. Both are prompt-engineering techniques, not architectural guarantees — the model is *asked* to behave this way, not *forced* to.

**Why we chose it**
Requirement: answers need to be traceable to actual document content, and the system needs to visibly refuse to answer when the retrieved context doesn't actually contain the answer, rather than confidently making something up.
Choice: a system prompt with an explicit grounding instruction + numbered context chunks + a "cite [n]" instruction, sent via proper system/user message roles to the LLM.
Benefit: cheap to implement (no extra infrastructure, no fine-tuning), and it visibly works — asking "what is the capital of France?" against a document that only contains a person's bio correctly returned "I don't know," even though the underlying model obviously knows the answer from pretraining. That's the grounding instruction actively overriding the model's own knowledge.
Cost: it's an instruction, not a constraint. Nothing in this system verifies that a cited chunk actually says what the model claims it says, or that the model didn't quietly blend in outside knowledge anyway. At this stage, trustworthiness of citations rests entirely on the model choosing to comply.
Rejected alternative: structured/function-call output (forcing the model to return citations as a validated JSON schema referencing real chunk IDs) or a separate verification pass that checks each claim against its cited chunk. Rejected for the naive-RAG phase because it adds real complexity (schema validation, a second LLM call or a claim-matching heuristic) before the basic retrieve→prompt→generate loop has even been observed working once — exactly the "framework abstractions after the mechanism is understood" rule from `CLAUDE.md`. Worth revisiting if citation reliability becomes the thing being evaluated (Phase 7).

**Soundbite**
"Grounding means I tell the model, explicitly, in the system prompt: only answer from the context I'm giving you, and if it's not in there, say you don't know. I proved this actually works, not just that I wrote the instruction — I asked a question with no answer in the retrieved document and got 'I don't know' back, even though the model obviously knows the real answer from pretraining. Citations are the same idea: each retrieved chunk gets a number, and the model has to tag which chunk each claim came from. It's honest to say this is instruction-based, not enforced — nothing here verifies the model didn't fudge a citation, and that's a real limitation I'd want to address before trusting this in anything higher-stakes."

**The gotcha**
Grounding failing doesn't look like an error — it looks like a plausible, confidently-worded wrong answer, because the model is fully capable of answering from pretraining and nothing stops it except an instruction it might not always follow. A second, quieter gotcha specific to this implementation: `search()` has no relevance threshold, so it always returns its top-k chunks even if none of them are actually relevant to the query — the LLM was handed an irrelevant "context" chunk when asked about France, and had to rely on the grounding instruction alone to recognize it wasn't useful. A weaker instruction, or a less compliant model, could have answered from the irrelevant chunk anyway, or from pretraining, and nothing in the current pipeline would have caught it.

**Self-test**
- What specifically makes grounding an instruction rather than a guarantee — what would have to change for it to become a hard constraint?
- Why does citing "[1]" next to a claim not actually prove the claim is true or that chunk 1 supports it?
- If `search()` returns an irrelevant top-1 chunk (because there's no similarity threshold), what are the two different ways the system could fail, and which one did the grounding instruction actually prevent in this project's testing?
- Why is system/user role separation in the prompt (rather than one concatenated string) not just a style preference?
- How would you design a test to catch a grounding failure automatically, rather than noticing it by manually reading an answer?

---

## 7. Chains vs. Graphs, State, and Reducers

**What it is**
A chain is a fixed, linear pipeline: step A always runs, then step B, then it's done — no branching, no revisiting an earlier step. That's exactly what `services/rag.py`'s `answer_question()` was: retrieve, then generate, always in that order, no way to say "actually, go back and retrieve again with a better query." A graph generalizes this: nodes (functions) connected by edges, with **shared state** flowing between them, and — the actual point of switching — edges can be *conditional*, so a node's output can decide which node runs next, including looping back to an earlier node. In LangGraph specifically, state is a typed dict (`RAGState` here), and each node returns only the keys it wants to update; the framework merges that partial update into the full state before the next node runs.

**Why we chose it**
Requirement: the naive RAG loop needs to eventually support retrying a bad first retrieval (Phase 6) — grading the retrieved chunks and, if they're weak, rewriting the query and trying again, bounded so it can't loop forever.
Choice: rebuild the existing retrieve→generate flow as a LangGraph `StateGraph` first, with **zero new behavior** — same two steps, same order, same output — before adding the actual grading/retry logic in a separate phase.
Benefit: this isolates "does the graph mechanism work" from "does the new self-correction logic work" — proven directly, by running the same question through both the old function and the new graph and getting matching answers and citations. If Phase 6 breaks something, it's provably not the graph plumbing's fault.
Cost: a graph is real added complexity over a plain function call — more moving parts (state shape, node wiring, compilation) for something that, at this stage, does exactly what five lines of Python already did. That cost is only worth paying because Phase 6 needs the conditional-looping capability a chain structurally cannot express.
Rejected alternative: skip straight to building the grading/retry logic *and* the graph structure in one step. Rejected because it's exactly the situation `CLAUDE.md` warns against — introducing a framework abstraction (LangGraph) at the same time as new logic (grading, rewriting) makes it impossible to tell, if something's wrong, whether the graph is misconfigured or the new logic is buggy.

**Soundbite**
"A chain is fixed — A then B then done. A graph adds state that flows between nodes and, more importantly, edges that can be conditional, so a node can decide to loop back instead of always moving forward. I didn't build the graph and the new retry logic at the same time — I rebuilt the *exact same* retrieve-then-generate flow as a 2-node graph first, with no new behavior, and proved it gives identical output to the plain function it replaced. That way, when Phase 6 adds the actual grading and retry loop, any bug I hit is provably in the new logic, not in the graph plumbing itself."

**The gotcha**
LangGraph's default behavior when a node returns a state update is to *overwrite* whatever was there — last writer wins. That's invisible and harmless right now because `retrieve` and `generate` never touch the same key. It stops being harmless the moment a loop is introduced: a retry counter that's supposed to *accumulate* across iterations (1, 2, 3...) would just get reset to whatever the node returns each time, silently breaking the "bounded" part of "bounded retries," unless it's given an explicit reducer (e.g., `Annotated[int, operator.add]`) that tells LangGraph how to combine the old value with the new one instead of replacing it. This is exactly the kind of thing that looks fine in a 2-node graph and breaks the moment you add a loop — worth testing for explicitly once Phase 6 lands, not assuming it "just works" the same way.

**Self-test**
- What can a graph express that a chain structurally cannot, and why does that matter for a self-correcting retrieval loop specifically?
- What does a LangGraph node actually return, and what does the framework do with that return value?
- Why does the default state-merge behavior (overwrite per key) work fine for `retrieve`→`generate` but fail silently once a retry loop is added?
- What's a reducer, concretely, and what problem does `Annotated[int, operator.add]` solve that the default merge behavior doesn't?
- Why was it worth building a graph with no new behavior first, instead of building the graph and the grading/retry logic together in one step?
