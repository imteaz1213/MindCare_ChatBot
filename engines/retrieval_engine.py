"""
Hybrid Retrieval Engine — "Proper input → proper output" নিশ্চিত করার জন্য
ডিজাইন করা multi-layer verification সহ retrieval system।

মূল আইডিয়া: single similarity score-এর উপর ভরসা না করে, একাধিক স্বাধীন
সিগন্যাল ব্যবহার করে decision নেওয়া — যাতে কোনো একটা layer ভুল করলেও
বাকি layer গুলো সেটা catch করতে পারে।

Layers (ক্রমানুসারে):
  1. Exact / near-exact match  -> সবচেয়ে নির্ভরযোগ্য, আগে চেক হয়
  2. Semantic embedding search -> paraphrase/সমার্থক প্রশ্ন ধরার জন্য
  3. Confidence-gap check      -> ambiguous case ধরার জন্য (top1 vs top2)
  4. Threshold gate            -> নিশ্চিত না হলে fallback, ভুল উত্তর না
"""

import re
import unicodedata
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util


class RetrievalEngine:

    def __init__(
        self,
        knowledge_base_path: str,
        similarity_threshold: float = 0.68,
        confidence_gap_threshold: float = 0.05,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
      
        self.similarity_threshold = similarity_threshold
        self.confidence_gap_threshold = confidence_gap_threshold

        self.model = SentenceTransformer(model_name)

        self.entries = self._load(knowledge_base_path)
        self.questions = [e["input"] for e in self.entries]

    
        self.normalized_lookup = {
            self._normalize(q): idx for idx, q in enumerate(self.questions)
        }

        if self.questions:
            self.question_vectors = self.model.encode(
                self.questions,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=True,
                batch_size=32,
            )
        else:
            self.question_vectors = None

    @staticmethod
    def _load(path: str) -> list:
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            return []
        except pd.errors.EmptyDataError:
            return []

        required_cols = {"input", "output"}
        if not required_cols.issubset(df.columns):
            raise ValueError(
                f"KB ফাইলে প্রয়োজনীয় কলাম নেই। দরকার: {required_cols}, "
                f"পাওয়া গেছে: {set(df.columns)}"
            )

        df = df.dropna(subset=["input", "output"])
        df = df.drop_duplicates(subset=["input"])
        return df[["input", "output"]].to_dict(orient="records")

    def reload(self, knowledge_base_path: str):
        self.__init__(
            knowledge_base_path,
            self.similarity_threshold,
            self.confidence_gap_threshold,
        )

    # ------------------------------------------------------------------
    # Text normalization — exact-match layer-এর জন্য
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize(text: str) -> str:
        """
        হালকা normalization: বাড়তি স্পেস, punctuation, case (ইংরেজি মিশ্রিত
        হলে) সরিয়ে দেয়, যাতে "আমার মন খারাপ।" আর "আমার মন খারাপ" একই ধরা পড়ে।
        """
        text = unicodedata.normalize("NFC", text.strip())
        text = re.sub(r"[।,!?.\"']", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.lower()

    # ------------------------------------------------------------------
    # Main search — এখানেই সব layer একসাথে কাজ করে
    # ------------------------------------------------------------------
    def search(self, clean_text: str) -> dict:
        if not self.questions or not clean_text:
            return {"matched": False, "answer": None, "score": 0.0, "method": None}

        # ---------- Layer 1: Exact / near-exact match ----------
        normalized_query = self._normalize(clean_text)
        if normalized_query in self.normalized_lookup:
            idx = self.normalized_lookup[normalized_query]
            return {
                "matched": True,
                "answer": self.entries[idx]["output"],
                "matched_question": self.entries[idx]["input"],
                "score": 1.0,
                "method": "exact_match",
            }

        # ---------- Layer 2: Semantic embedding search ----------
        query_vec = self.model.encode(
            clean_text, convert_to_tensor=True, normalize_embeddings=True
        )
        similarities = util.cos_sim(query_vec, self.question_vectors)[0]
        sims_np = similarities.cpu().numpy()

        # top-2 বের করছি confidence-gap check এর জন্য
        top2_idx = np.argsort(sims_np)[-2:][::-1]
        best_idx = int(top2_idx[0])
        best_score = float(sims_np[best_idx])
        second_score = float(sims_np[top2_idx[1]]) if len(top2_idx) > 1 else 0.0

        # ---------- Layer 3: Threshold gate ----------
        if best_score < self.similarity_threshold:
            return {
                "matched": False,
                "answer": None,
                "score": best_score,
                "method": "semantic_below_threshold",
            }

        # ---------- Layer 4: Confidence-gap check ----------
        gap = best_score - second_score
        if gap < self.confidence_gap_threshold:
            # দুটো candidate প্রায় সমান স্কোর — মানে system নিশ্চিত না,
            # ভুল answer দেওয়ার চেয়ে fallback করা নিরাপদ।
            return {
                "matched": False,
                "answer": None,
                "score": best_score,
                "method": "ambiguous_low_confidence_gap",
                "runner_up_score": second_score,
            }

        return {
            "matched": True,
            "answer": self.entries[best_idx]["output"],
            "matched_question": self.entries[best_idx]["input"],
            "score": best_score,
            "method": "semantic_match",
        }


if __name__ == "__main__":
    # ছোট ডেমো — নিজের CSV পাথ বসিয়ে টেস্ট করুন
    engine = HybridRetrievalEngine("knowledge_base.csv")

    test_queries = [
        "আমার মন খারাপ",  # exact-ish
        "কাজে মন বসে না, চাপ লাগছে",  # paraphrase
        "আজকে আবহাওয়া কেমন",  
    ]

    for q in test_queries:
        result = engine.search(q)
        print(f"\nQuery: {q}")
        print(f"Result: {result}")