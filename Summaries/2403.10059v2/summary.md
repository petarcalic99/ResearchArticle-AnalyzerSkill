# REPOFORMER: Selective Retrieval for Repository-Level Code Completion

**Summary:** The paper introduces REPOFORMER, a code language model fine-tuned via self-supervised learning to decide *when* cross-file retrieval is worthwhile and to robustly exploit it, achieving state-of-the-art repository-level code completion while cutting inference latency by up to 70%.

## Introduction
Existing retrieval-augmented generation (RAG) systems for repository-level code completion always retrieve cross-file context, even though up to 80% of those retrievals are unhelpful or actively harmful and impose large latency costs. The authors propose a *selective RAG* framework in which a single code LM self-evaluates whether retrieval will improve its output and abstains when it will not.

## What they did
- Diagnosed the problem: across RepoEval API and function completion, retrieval improves only ~20% of instances for code LMs (CodeGen-Mono 2B/16B, StarCoderBase 1B, StarCoder 16B), leaves >60% unchanged, and degrades ~20%.
- Formulated *self-selective RAG* as an extension of fill-in-the-middle (Figure 2): after an `<eof>` token the model emits `<cc>` to self-trigger retrieval or an empty token to abstain, all in one left-to-right pass (architecture overview in Figure 1).
- Built self-supervised training data from ~18k permissively licensed Python repos in the Stack, sampling 240k chunk and 120k function completion instances, and contrastively labeling each by whether retrieved context improves a StarCoderBase-1B's Edit Similarity beyond a threshold.
- Designed a multi-task objective combining a self-evaluation loss (L_eval) and a code-generation loss (L_gen), and fine-tuned StarCoderBase at 1B/3B/7B/16B scales (REPOFORMER-1B/3B/7B/16B), plus a multilingual variant.
- Evaluated on RepoEval, CrossCodeEval, and a newly created long-form benchmark, CrossCodeLongEval (chunk + function completion from 1500 Python repos), using exact match, edit similarity, and unit-test pass rate.
- Tested REPOFORMER-1B as a plug-and-play selective-retrieval policy for larger black-box models (StarCoderBase-7B/16B, CodeGen25, Code Llama, ChatGPT/gpt-3.5-turbo).

## Key findings & results
- REPOFORMER's threshold-selection strategy beats same-sized StarCoderBase on every task and metric, by more than 3 absolute edit-similarity points across multiple tasks; REPOFORMER-3B matches or exceeds the 5x-larger StarCoder-16B on several metrics.
- REPOFORMER-16B sets a new state of the art, outperforming the strongest StarCoder baseline by ~3% averaged across all tasks.
- Selective retrieval yields up to 70% inference speedup without hurting accuracy; with REPOFORMER-1B as the model, threshold selection improves *both* accuracy and latency (e.g., line completion at ~62% RAG vs. always-retrieving), while greedy selection performs RAG on only ~18-20% of instances for larger latency gains at ~1.0 ES cost.
- As a standalone policy, REPOFORMER-1B reduces latency of larger LMs (including ChatGPT and Code Llama) by ~25% while *improving* their accuracy (Table 4).
- Retrieval abstention is precise (>0.8 correct on all tasks except RepoEval function completion at 0.78), and the model remains robust to noisy retrieved context (Figure 6); behavior is stable across thresholds, with ~50% latency reduction at threshold 0.4 (Figure 4).

## Methodology & limitations
REPOFORMER turns the retrieval decision into a near-free single forward pass: the model reads the left and right in-file context, predicts the probability of a `<cc>` token, and only invokes the (default Jaccard-similarity) retriever and appends cross-file chunks if that probability exceeds a task-specific threshold (≈0.15-0.2), otherwise completing directly. Training mines self-supervision by contrasting a code LM's output quality with versus without retrieval, so the policy reflects both the model's self-knowledge and the question's dependence on cross-file information, with no external oracle LM or knowledge store needed. The authors caution that their training labels rely on lexical Edit Similarity, which yields suboptimal calibration for function completion (where unit-test correctness is the real target) and call for better, scalable labeling; they also note the policy is uniform across repositories (some are inherently more RAG-friendly) and that, as with any RAG system, safeguards are needed to prevent leakage of sensitive data from the retrieval store. They additionally flag speculative decoding and personalized retrieval as open directions.

## About the authors
The lead author, Di Wu, conducted this work as an intern at AWS AI Labs while a researcher at the University of California, Los Angeles (UCLANLP), with co-authors from AWS AI Labs; a reliable publication count, h-index, and citation total could not be established because OpenAlex disambiguation conflates this name with several unrelated researchers.
