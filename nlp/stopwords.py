"""
Small Bangla stopword list. Used ONLY for the word-overlap accuracy
gate in the retrieval / generative-corpus-fallback engines -- not for
TF-IDF vectorization itself.
"""

STOPWORDS = set(
    """
    আমি আমার আমাকে আমাদের তুমি তোমার তোমাকে সে তার তাকে এই ওই যে কি কেন কীভাবে
    কিভাবে না নাই হয় হয়ে হচ্ছে হবে হলো ছিল ছিলাম করে করি করছে করবো করবে করলো
    মনে মাঝে মাঝেমধ্যে মাঝেমাঝে সব সবার সবাই অনেক একটু কিছু কিছুটা থেকে সাথে
    নিয়ে জন্য পারছি পারি পারছে লাগে লাগছে আজকাল আজকে আজ গতকাল কাল এখন তখন
    যখন তখনই আছে আছি থাকে থাকি যায় যাচ্ছে গেছে গেল দিয়ে দিতে নেই কোনো কোন
    এবং ও তো যদি কেউ
    """.split()
)


def significant_tokens(clean_words: list) -> set:
    """Given already-cleaned/tokenized words, return the subset that
    are meaningful content words (not generic connectors/pronouns).
    """
    return set(w for w in clean_words if len(w) >= 3 and w not in STOPWORDS)