# REPOFORMER: Selective Retrieval for Repository-Level Code Completion

**Summary:** The paper shows that always retrieving cross-file context for repository-level code completion is often wasteful or harmful, and introduces REPOFORMER — a code LM fine-tuned to self-decide when retrieval is needed and to robustly use it — achieving state-of-the-art accuracy with up to 70% inference speedup.

## Introduction
Existing retrieval-augmented generation (RAG) methods for repository-level code completion invariably retrieve cross-file context, yet up to 80% of those retrievals fail to help and many actively degrade output quality while adding large latency overhead. The authors propose a selective RAG framework in which a single code LM both decides whether to retrieve (via self-assessment) and performs the completion, abstaining from retrieval when it is unlikely to help.

## What they did
- Identified the core problem empirically: across four code LMs (CodeGen-Mono 2B/16B, StarCoderBase-1B, StarCoder-16B) on RepoEval, retrieval improved only ~20% of instances, left ~60% unchanged, and harmed ~20%.
- Formulated "self-selective RAG" as an extension of fill-in-the-middle: after a new `<eof>` token, the LM emits `<cc>` to trigger retrieval or abstains, all in a single left-to-right pass (Figure 2); the decision can be thresholded on the probability of `<cc>`.
- Built self-supervised training data from ~18k permissively-licensed Python repositories in the Stack: sampled chunk and function blanks (240k + 120k instances), retrieved cross-file context with Jaccard similarity, and labeled each instance by whether retrieval raised StarCoderBase-1B's Edit Similarity beyond a threshold T.
- Trained a multi-task objective combining a self-evaluation loss (predicting `<cc>`) and a generation loss, fine-tuning StarCoderBase at 1B/3B/7B/16B sizes (and a multilingual variant on Python, Java, C#, TypeScript).
- Introduced CrossCodeLongEval, a new large-scale chunk- and function-completion benchmark (944/1460 repositories, ~6500 instances) derived from CrossCodeEval repositories, and evaluated on RepoEval and CrossCodeEval as well.
- Tested REPOFORMER-1B as a plug-and-play selective-retrieval policy in front of larger black-box generators (StarCoderBase, Code Llama, CodeGen25, ChatGPT/gpt-3.5-turbo).

## Key findings & results
- Selective retrieval beats same-sized "always retrieving": REPOFORMER's threshold strategy improves over StarCoderBase by more than 3 absolute ES points across multiple tasks; REPOFORMER-3B matches/exceeds the 5x-larger StarCoder-16B on several metrics, and REPOFORMER-16B sets a new state of the art, ~3% above the strongest StarCoder baseline averaged over tasks.
- Efficiency: threshold selection improves both accuracy and latency over always retrieving; greedy selection yields up to ~69% speedup on API completion (running RAG on only ~18% of instances) at a minor ~1.0 ES cost. With dense retrieval, threshold selection delivers more than 70% speedup.
- As a policy for larger generators, REPOFORMER-1B cuts their latency by roughly 25% while slightly improving accuracy across StarCoderBase-7B/16B, Code Llama-7B/16B, CodeGen25-7B, and ChatGPT (Table 4).
- Decision quality: retrieval abstentions are correct for over 80% of instances on all tasks (0.78 on RepoEval function completion, Figure 5); predictions are near-calibrated for line/API completion but poorly calibrated for function completion under the unit-test metric.
- Ablations confirm both losses matter: training only on fill-in-the-middle (no cross-file context) hurts RAG performance, and merging the two losses collapses the selective decision (probability of `<cc>` becomes ~1).

## Methodology & limitations
A single code LM is fine-tuned so that, after seeing the file's left and right context, it forecasts via a special token whether cross-file retrieval would raise its own output quality; if so it triggers a Jaccard-similarity retriever and completes with the retrieved chunks, otherwise it completes in-file — supervision comes entirely from contrasting the model's own ES with and without retrieval on simulated RAG instances, requiring no oracle LM, extra modules, or external knowledge store. The authors acknowledge several caveats: training labels rely on lexical Edit Similarity, which yields a weak and poorly-calibrated signal for function completion (they call for better correctness-labeling methods); a single self-assessment may be inadequate for long-form generation; the policy is uniform across repositories whereas some repositories are inherently more RAG-friendly (personalized policies are left to future work); and RAG systems raise data-leakage risks from the retrieval database.

## About the authors
The paper lists Di Wu as first author, a University of California, Los Angeles PhD student who did this work during an internship at AWS AI Labs (correspondence is handled by senior author Wasi Uddin Ahmad, then at UCLA/AWS), with the remaining authors (Dejiao Zhang, Murali Krishna Ramanathan, Xiaofei Ma) at AWS AI Labs; OpenAlex returns multiple unrelated researchers named "Di Wu" and none cleanly matches this UCLA NLP profile, so no reliable bibliometrics can be attached.

## Publication & credibility
Published in the Proceedings of the 41st International Conference on Machine Learning (ICML 2024), PMLR vol. 235, Vienna — as stated in the paper's own camera-ready footer and acknowledgements (anonymous reviewers are thanked). ICML is a top-tier, highly selective machine-learning venue, so this is a strongly credible peer-reviewed publication.
