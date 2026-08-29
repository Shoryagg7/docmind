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
