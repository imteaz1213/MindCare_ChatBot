
import re
import unicodedata

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi


class RetrievalEngine:
 

    def __init__(
        self,
        knowledge_base_path: str,
        similarity_threshold: float = 0.50,
        confidence_gap_threshold: float = 0.05,
        tfidf_weight: float = 0.45,
        bm25_weight: float = 0.55,
    ):
        self.similarity_threshold = similarity_threshold
        self.confidence_gap_threshold = confidence_gap_threshold

        self.tfidf_weight = tfidf_weight
        self.bm25_weight = bm25_weight

        self.entries = self._load(knowledge_base_path)

        self.questions = [
            str(e["input"])
            for e in self.entries
        ]


        self.normalized_lookup = {
            self._normalize(q): idx
            for idx, q in enumerate(self.questions)
        }


        self.documents = []

        for entry in self.entries:

            input_text = str(entry.get("input", ""))

            instruction_text = str(
                entry.get("instruction", "")
            )

            document = f"{input_text} {instruction_text}".strip()

            self.documents.append(
                self._normalize(document)
            )


        if self.documents:

            self.tfidf_vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=1,
                sublinear_tf=True,
            )

            self.tfidf_matrix = (
                self.tfidf_vectorizer.fit_transform(
                    self.documents
                )
            )

        else:

            self.tfidf_vectorizer = None
            self.tfidf_matrix = None

        if self.documents:

            tokenized_documents = [
                self._tokenize(doc)
                for doc in self.documents
            ]

            self.bm25 = BM25Okapi(
                tokenized_documents
            )

        else:

            self.bm25 = None


    @staticmethod
    def _load(path: str) -> list:

        try:

            df = pd.read_csv(path)

        except FileNotFoundError:

            return []

        except pd.errors.EmptyDataError:

            return []


        required_cols = {
            "input",
            "output"
        }

        if not required_cols.issubset(df.columns):

            raise ValueError(
                f"KB ফাইলে প্রয়োজনীয় কলাম নেই। "
                f"দরকার: {required_cols}, "
                f"পাওয়া গেছে: {set(df.columns)}"
            )

      
        if "instruction" not in df.columns:

            df["instruction"] = ""

       

        df = df.dropna(
            subset=[
                "input",
                "output"
            ]
        )


        df = df.drop_duplicates(
            subset=["input"]
        )

        return df[
            [
                "input",
                "instruction",
                "output"
            ]
        ].to_dict(
            orient="records"
        )

    

    def reload(
        self,
        knowledge_base_path: str
    ):

        self.__init__(
            knowledge_base_path,
            self.similarity_threshold,
            self.confidence_gap_threshold,
            self.tfidf_weight,
            self.bm25_weight,
        )

    @staticmethod
    def _normalize(text: str) -> str:

        if not text:
            return ""

       
        text = unicodedata.normalize(
            "NFC",
            str(text).strip()
        )

       
        text = text.lower()

       
        text = re.sub(
            r"""[।,!?\.\'"\-_:;()\[\]{}<>/\\|@#$%^&*+=~`]+""",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()


    @staticmethod
    def _tokenize(text: str):

        normalized = RetrievalEngine._normalize(
            text
        )

        if not normalized:
            return []

        return normalized.split()

    @staticmethod
    def _normalize_scores(scores):

        scores = np.asarray(
            scores,
            dtype=np.float32
        )

        if len(scores) == 0:
            return scores

        min_score = scores.min()
        max_score = scores.max()

    
        if max_score - min_score < 1e-8:

            if max_score > 0:
                return np.ones_like(scores)

            return np.zeros_like(scores)

        return (
            (scores - min_score)
            / (max_score - min_score)
        )


    def search(
        self,
        clean_text: str
    ) -> dict:

        if (
            not self.questions
            or not clean_text
        ):

            return {
                "matched": False,
                "answer": None,
                "score": 0.0,
                "method": None,
            }

        normalized_query = self._normalize(
            clean_text
        )

        if not normalized_query:

            return {
                "matched": False,
                "answer": None,
                "score": 0.0,
                "method": None,
            }


        if normalized_query in self.normalized_lookup:

            idx = self.normalized_lookup[
                normalized_query
            ]

            return {
                "matched": True,
                "answer": self.entries[idx]["output"],
                "matched_question": self.entries[idx]["input"],
                "score": 1.0,
                "method": "exact_match",
            }


        query_vector = (
            self.tfidf_vectorizer.transform(
                [normalized_query]
            )
        )

        tfidf_scores = cosine_similarity(
            query_vector,
            self.tfidf_matrix
        )[0]

       
        tfidf_normalized = (
            self._normalize_scores(
                tfidf_scores
            )
        )

        query_tokens = self._tokenize(
            normalized_query
        )

        bm25_scores = self.bm25.get_scores(
            query_tokens
        )

        bm25_normalized = (
            self._normalize_scores(
                bm25_scores
            )
        )


        combined_scores = (
            self.tfidf_weight
            * tfidf_normalized
        ) + (
            self.bm25_weight
            * bm25_normalized
        )

        if len(combined_scores) == 1:

            top2_idx = np.array(
                [0]
            )

        else:

            top2_idx = np.argsort(
                combined_scores
            )[-2:][::-1]

        best_idx = int(
            top2_idx[0]
        )

        best_score = float(
            combined_scores[best_idx]
        )

        if len(top2_idx) > 1:

            second_idx = int(
                top2_idx[1]
            )

            second_score = float(
                combined_scores[second_idx]
            )

        else:

            second_score = 0.0


        if best_score < self.similarity_threshold:

            return {
                "matched": False,
                "answer": None,
                "score": best_score,
                "method": "below_threshold",
                "tfidf_score": float(
                    tfidf_normalized[best_idx]
                ),
                "bm25_score": float(
                    bm25_normalized[best_idx]
                ),
            }


        gap = (
            best_score
            - second_score
        )

        if (
            gap
            < self.confidence_gap_threshold
        ):

            return {
                "matched": False,
                "answer": None,
                "score": best_score,
                "method": "ambiguous_low_confidence_gap",
                "runner_up_score": second_score,
                "confidence_gap": gap,
                "matched_question": self.entries[
                    best_idx
                ]["input"],
            }


        return {
            "matched": True,

            "answer": self.entries[
                best_idx
            ]["output"],

            "matched_question": self.entries[
                best_idx
            ]["input"],

            "score": best_score,

            "method": "hybrid_tfidf_bm25",

            "tfidf_score": float(
                tfidf_normalized[best_idx]
            ),

            "bm25_score": float(
                bm25_normalized[best_idx]
            ),

            "confidence_gap": gap,
        }



if __name__ == "__main__":

    engine = RetrievalEngine(
        "knowledge_base.csv",

        similarity_threshold=0.50,

        confidence_gap_threshold=0.05,

        tfidf_weight=0.45,

        bm25_weight=0.55,
    )

    test_queries = [

        "আমার মন খারাপ",

        "কাজে মন বসে না, চাপ লাগছে",

        "আজকে আবহাওয়া কেমন",

        "আমি অনেক stressed",

    ]

    for query in test_queries:

        result = engine.search(
            query
        )

        print(
            f"\nQuery: {query}"
        )

        print(
            "Result:",
            result
        )