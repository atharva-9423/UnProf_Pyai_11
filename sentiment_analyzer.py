"""
sentiment_analyzer.py
----------------------
Day 11 Task: Product Review Sentiment Analyzer

- Loads a dataset of 100 product reviews (reviews.csv)
- Classifies each review as Positive, Negative, or Neutral using
  TextBlob and VADER (industry-standard sentiment tools)
- Prints the total count of each sentiment class
- Generates a bar chart and a pie chart summarizing the results

HOW TO RUN
----------
1. Install dependencies:
       pip install textblob vaderSentiment pandas matplotlib
       python -m textblob.download_corpora   (only needed the first time, for TextBlob)

2. (Optional) regenerate the dataset:
       python generate_dataset.py

3. Run the analyzer:
       python sentiment_analyzer.py

Note: If textblob / vaderSentiment are not installed (e.g. no internet
access), this script automatically falls back to a small built-in
lexicon-based scorer so it still runs end-to-end. Install the real
libraries for more accurate, production-grade results.
"""

import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# 1. Try to import the real TextBlob / VADER libraries.
#    Fall back to a lightweight built-in scorer if they're unavailable.
# ---------------------------------------------------------------------------
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False


# ---------------------------------------------------------------------------
# 2. Fallback lexicon-based scorer (used only if the libraries above
#    are not installed). Mimics the polarity-score idea behind
#    TextBlob/VADER: returns a compound score between -1 and +1.
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = {
    "love", "amazing", "great", "excellent", "perfect", "best", "happy",
    "fantastic", "impressive", "durable", "recommend", "comfortable",
    "smooth", "fast", "outstanding", "thrilled", "sturdy", "beautiful",
    "flawlessly", "satisfied", "delicious", "premium", "easy", "clear",
    "worth", "reliable", "top",
}
_NEGATIVE_WORDS = {
    "terrible", "awful", "disappointed", "broke", "worst", "waste",
    "rude", "damaged", "poor", "cheaply", "regret", "flimsy", "slow",
    "cracked", "defective", "horrible", "useless", "nightmare",
    "misleading", "noisy", "irritating", "snapped", "faded", "scratches",
    "unusable",
}
_NEGATIONS = {"not", "no", "never", "n't", "without"}


def _fallback_score(text: str) -> float:
    words = text.lower().replace(",", "").replace(".", "").split()
    score = 0
    for i, w in enumerate(words):
        prev = words[i - 1] if i > 0 else ""
        if w in _POSITIVE_WORDS:
            score += -1 if prev in _NEGATIONS else 1
        elif w in _NEGATIVE_WORDS:
            score += 1 if prev in _NEGATIONS else -1
    if not words:
        return 0.0
    return max(-1.0, min(1.0, score / max(3, len(words) ** 0.5)))


# ---------------------------------------------------------------------------
# 3. Sentiment scoring functions
# ---------------------------------------------------------------------------
def get_textblob_polarity(text: str) -> float:
    """Returns polarity score in range [-1, 1] using TextBlob (or fallback)."""
    if TEXTBLOB_AVAILABLE:
        return TextBlob(text).sentiment.polarity
    return _fallback_score(text)


_vader_analyzer = SentimentIntensityAnalyzer() if VADER_AVAILABLE else None


def get_vader_compound(text: str) -> float:
    """Returns compound score in range [-1, 1] using VADER (or fallback)."""
    if VADER_AVAILABLE:
        return _vader_analyzer.polarity_scores(text)["compound"]
    return _fallback_score(text)


def classify(score: float, pos_threshold: float = 0.05, neg_threshold: float = -0.05) -> str:
    """Standard VADER-style thresholding to classify a polarity score."""
    if score >= pos_threshold:
        return "Positive"
    elif score <= neg_threshold:
        return "Negative"
    return "Neutral"


# ---------------------------------------------------------------------------
# 4. Main pipeline
# ---------------------------------------------------------------------------
def main():
    df = pd.read_csv("reviews.csv")

    df["textblob_score"] = df["review_text"].apply(get_textblob_polarity)
    df["vader_score"] = df["review_text"].apply(get_vader_compound)

    df["textblob_sentiment"] = df["textblob_score"].apply(classify)
    df["vader_sentiment"] = df["vader_score"].apply(classify)

    # Final sentiment = VADER's classification (VADER is purpose-built
    # for short, informal text like reviews and social media posts).
    df["final_sentiment"] = df["vader_sentiment"]

    df.to_csv("reviews_with_sentiment.csv", index=False)

    counts = df["final_sentiment"].value_counts().reindex(
        ["Positive", "Negative", "Neutral"], fill_value=0
    )

    print("=" * 50)
    print("PRODUCT REVIEW SENTIMENT ANALYSIS - DAY 11")
    print("=" * 50)
    print(f"TextBlob available : {TEXTBLOB_AVAILABLE}")
    print(f"VADER available    : {VADER_AVAILABLE}")
    print("-" * 50)
    print("Sentiment counts (based on VADER classification):")
    for label, count in counts.items():
        print(f"  {label:9s}: {count}")
    print("-" * 50)
    print(f"Total reviews analyzed: {len(df)}")
    print("Detailed results saved to reviews_with_sentiment.csv")

    # -----------------------------------------------------------------
    # 5. Visualization: bar chart + pie chart, saved as one PNG
    # -----------------------------------------------------------------
    colors = {"Positive": "#4CAF50", "Negative": "#E53935", "Neutral": "#FDD835"}
    bar_colors = [colors[label] for label in counts.index]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].bar(counts.index, counts.values, color=bar_colors)
    axes[0].set_title("Review Sentiment Counts")
    axes[0].set_xlabel("Sentiment")
    axes[0].set_ylabel("Number of Reviews")
    for i, v in enumerate(counts.values):
        axes[0].text(i, v + 1, str(v), ha="center", fontweight="bold")

    axes[1].pie(
        counts.values,
        labels=counts.index,
        autopct="%1.1f%%",
        colors=bar_colors,
        startangle=90,
    )
    axes[1].set_title("Review Sentiment Distribution")

    plt.suptitle("Product Review Sentiment Analyzer — 100 Reviews", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig("sentiment_summary_chart.png", dpi=150)
    print("Chart saved to sentiment_summary_chart.png")


if __name__ == "__main__":
    main()
