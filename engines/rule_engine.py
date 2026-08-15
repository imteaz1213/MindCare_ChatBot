import pandas as pd


class RuleBasedEngine:

    def __init__(self, safety_rules_path: str):
        self.rules = self._load(safety_rules_path)

    @staticmethod
    def _load(path: str) -> list:
        try:
            df = pd.read_excel(path)
        except FileNotFoundError:
            return []

        df = df.dropna(subset=["category", "keywords", "response"])

        rules = []
        for _, row in df.iterrows():
            keywords = [
                kw.strip().lower()
                for kw in str(row["keywords"]).split(",")
                if kw.strip()
            ]
            rules.append(
                {
                    "category": row["category"],
                    "keywords": keywords,
                    "response": row["response"],
                }
            )
        return rules

    def reload(self, safety_rules_path: str):
     
        self.rules = self._load(safety_rules_path)

    def assess(self, clean_text: str) -> dict:
       
        for rule in self.rules:
            matched = [kw for kw in rule["keywords"] if kw in clean_text]
            if matched:
                return {
                    "triggered": True,
                    "category": rule["category"],
                    "matched_keywords": matched,
                    "response": rule["response"],
                }

        return {
            "triggered": False,
            "category": None,
            "matched_keywords": [],
            "response": None,
        }
