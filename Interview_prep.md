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
