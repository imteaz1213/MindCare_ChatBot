class Orchestrator:
    

    def __init__(self, rule_engine, retrieval_engine, generative_engine):
        self.rule_engine = rule_engine
        self.retrieval_engine = retrieval_engine
        self.generative_engine = generative_engine

    def route(self, processed_input: dict) -> dict:
        clean_text = processed_input["clean_text"]

        crisis_result = self.rule_engine.assess(clean_text)
        if crisis_result["triggered"]:
            return {
                "engine_used": "rule_based",
                "category": crisis_result["category"],
                "response": crisis_result["response"],
                "metadata": {"matched_keywords": crisis_result["matched_keywords"]},
            }

        
        retrieval_result = self.retrieval_engine.search(clean_text)
        if retrieval_result["matched"]:
            return {
                "engine_used": "retrieval",
                "category": None,
                "response": retrieval_result["answer"],
                "metadata": {
                    "matched_question": retrieval_result["matched_question"],
                    "score": retrieval_result["score"],
                },
            }
       
        print("Calling Gemini Now...")
        generative_response = self.generative_engine.generate(
            processed_input["raw_text"]
        )
        return {
            "engine_used": "generative",
            "category": None,
            "response": generative_response,
            "metadata": {},
        }


        