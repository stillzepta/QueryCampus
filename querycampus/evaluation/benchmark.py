"""
QueryCampus Evaluation & Benchmarking Suite.
Measures End-to-End Latency Breakdown and Accuracy across 50 Campus Queries.
Complies with IEEE GITCON 2025 Paper Sec. IV, Table III, and Figure 5.
Maintained by: Amannat (Integration, Testing & Pitch Lead)
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from querycampus.config import BASE_DIR, TOP_K
from querycampus.pipeline.vector_store import ChromaVectorStore
from querycampus.pipeline.retrieval import HybridRetriever
from querycampus.llm.prompts import StrictPromptEngine
from querycampus.llm.router import LLMRouter


DATASET_PATH = Path(__file__).resolve().parent / "test_dataset.json"


class EvaluationBenchmark:
    def __init__(
        self,
        dataset_path: Path = DATASET_PATH,
        top_k: int = TOP_K,
        model_name: Optional[str] = None,
    ):
        self.dataset_path = dataset_path
        self.top_k = top_k
        self.model_name = model_name
        self.vector_store = ChromaVectorStore()
        self.retriever = HybridRetriever(self.vector_store)
        self.prompt_engine = StrictPromptEngine()
        self.router = LLMRouter()

    def load_dataset(self) -> List[Dict[str, Any]]:
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_benchmark(self, max_queries: Optional[int] = None, run_generation: bool = True) -> Dict[str, Any]:
        """Runs evaluation over the benchmark test queries."""
        items = self.load_dataset()
        if max_queries:
            items = items[:max_queries]

        total_queries = len(items)
        retrieval_hits_count = 0
        correctness_count = 0

        embed_times: List[float] = []
        retrieval_times: List[float] = []
        gen_times: List[float] = []

        print(f"\n================================================================================")
        print(f"🚀 QUERYCAMPUS BENCHMARK EVALUATION (Testing {total_queries} Campus Queries)")
        print(f"================================================================================")

        for idx, item in enumerate(items, start=1):
            query = item["query"]
            expected_keywords = [k.lower() for k in item.get("expected_keywords", [])]

            # 1. Retrieval
            hits, emb_t, ret_t = self.retriever.retrieve(query, top_k=self.top_k)
            embed_times.append(emb_t)
            retrieval_times.append(ret_t)

            # Check Top-k Retrieval Accuracy
            retrieved_text = " ".join([h.get("text", "") for h in hits]).lower()
            hit_success = any(kw in retrieved_text for kw in expected_keywords)
            if hit_success:
                retrieval_hits_count += 1

            # 2. Generation (optional / sampled)
            gen_t = 0.0
            response_text = ""
            correct_response = False

            if run_generation:
                prompt = self.prompt_engine.build_prompt(query, hits)
                gen_res = self.router.generate(prompt, model_name=self.model_name)
                gen_t = gen_res.generation_time
                gen_times.append(gen_t)
                response_text = gen_res.text
                correct_response = any(kw in response_text.lower() for kw in expected_keywords)
                if correct_response:
                    correctness_count += 1
            else:
                correct_response = hit_success
                if correct_response:
                    correctness_count += 1

            status_symbol = "✅" if hit_success else "❌"
            print(f"[{idx:02d}/{total_queries}] {status_symbol} '{query[:45]}...' | Emb: {emb_t:.3f}s | Ret: {ret_t:.3f}s" + (f" | Gen: {gen_t:.2f}s" if run_generation else ""))

        # Aggregated Metrics
        avg_emb = sum(embed_times) / len(embed_times) if embed_times else 0.0
        avg_ret = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0.0
        avg_gen = sum(gen_times) / len(gen_times) if gen_times else 0.0
        avg_total = avg_emb + avg_ret + avg_gen

        retrieval_accuracy = (retrieval_hits_count / total_queries) * 100.0
        response_correctness = (correctness_count / total_queries) * 100.0
        failure_rate = 100.0 - retrieval_accuracy

        summary = {
            "total_queries": total_queries,
            "top_k": self.top_k,
            "avg_query_embedding_time_sec": avg_emb,
            "avg_chroma_retrieval_time_sec": avg_ret,
            "avg_llm_generation_time_sec": avg_gen,
            "avg_total_latency_sec": avg_total,
            "top_k_retrieval_accuracy_pct": retrieval_accuracy,
            "response_correctness_pct": response_correctness,
            "failure_rate_pct": failure_rate,
        }

        self._print_report(summary, run_generation)
        return summary

    def _print_report(self, s: Dict[str, Any], ran_generation: bool) -> None:
        print("\n" + "=" * 80)
        print("📊 BENCHMARK SUMMARY & LATENCY MEASUREMENTS (IEEE GITCON 2025 Alignment)")
        print("=" * 80)
        print(f"Queries Evaluated        : {s['total_queries']}")
        print(f"Top-{s['top_k']} Retrieval Accuracy  : {s['top_k_retrieval_accuracy_pct']:.1f}% (Paper Target: 92.0%)")
        print(f"Response Correctness     : {s['response_correctness_pct']:.1f}% (Paper Target: 88.0%)")
        print(f"Failure Rate             : {s['failure_rate_pct']:.1f}% (Paper Target: 8.0%)")
        print("-" * 80)
        print("⏱️ LATENCY BREAKDOWN (Table III Comparison):")
        print(f"  • Query Embedding      : {s['avg_query_embedding_time_sec']:.3f} s  (Paper: 0.7 s)")
        print(f"  • Chroma Retrieval     : {s['avg_chroma_retrieval_time_sec']:.3f} s  (Paper: 0.3 s)")
        if ran_generation:
            print(f"  • LLM Generation       : {s['avg_llm_generation_time_sec']:.3f} s  (Paper: 10.1 s on CPU)")
        print(f"  • Total End-to-End     : {s['avg_total_latency_sec']:.3f} s  (Paper: 11.1 s)")
        print("=" * 80 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="QueryCampus Benchmark Evaluator")
    parser.add_argument("--count", type=int, default=None, help="Number of queries to run (default: all 50)")
    parser.add_argument("--fast", action="store_true", help="Evaluate retrieval accuracy without invoking full LLM generation")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model name")
    args = parser.parse_args()

    bench = EvaluationBenchmark(model_name=args.model)
    bench.run_benchmark(max_queries=args.count, run_generation=not args.fast)


if __name__ == "__main__":
    main()
