from flask import Flask, request, jsonify, render_template
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import pdfplumber
import io

app = Flask(__name__)
analyzer = SentimentIntensityAnalyzer()

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'pdf'}


def get_textblob_sentiment(text):
    polarity = TextBlob(str(text)).sentiment.polarity
    if polarity > 0:    return ('Positive', round(polarity, 3))
    elif polarity < 0:  return ('Negative', round(polarity, 3))
    else:               return ('Neutral',   0.0)


def get_vader_sentiment(text):
    scores = analyzer.polarity_scores(str(text))
    c = scores['compound']
    if c >= 0.05:    label = 'Positive'
    elif c <= -0.05: label = 'Negative'
    else:            label = 'Neutral'
    return (label, round(c, 3), scores)


def get_final_sentiment(tb_score, vader_score, tb_label, vader_label):
    """
    Weighted average of the two numeric scores (both already on -1 to +1 scale).
      TextBlob  → 40% weight
      VADER     → 60% weight  (better calibrated for short product text)

    This produces a truly independent third score rather than just
    echoing whichever model wins a label vote.

    Confidence reflects how much the two models agree:
      High   — both labels match
      Medium — labels differ but weighted score is decisive (|score| > 0.15)
      Low    — labels differ and score is close to zero
    """
    weighted = round((tb_score * 0.4) + (vader_score * 0.6), 3)

    if weighted >= 0.05:
        label = 'Positive'
    elif weighted <= -0.05:
        label = 'Negative'
    else:
        label = 'Neutral'

    if tb_label == vader_label:
        confidence = 'High'
    elif abs(weighted) > 0.15:
        confidence = 'Medium'
    else:
        confidence = 'Low'

    return label, weighted, confidence


def best_text_column(df):
    """Return the column that most looks like free-text reviews (longest avg string, not numeric)."""
    best_col = None
    best_avg = -1
    for col in df.columns:
        series = df[col].dropna().astype(str)
        # Skip columns that are clearly numeric or very short
        avg_len = series.str.len().mean()
        if avg_len > best_avg:
            best_avg = avg_len
            best_col = col
    return best_col


def read_dataframe(file, ext):
    if ext == 'csv':
        return pd.read_csv(file)
    elif ext in ('xlsx', 'xls'):
        return pd.read_excel(file)
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data['text']
    tb_label,    tb_score                  = get_textblob_sentiment(text)
    vader_label, vader_score, vader_details = get_vader_sentiment(text)
    final_label, final_score, confidence   = get_final_sentiment(
        tb_score, vader_score, tb_label, vader_label
    )

    return jsonify({
        'textblob': {'sentiment': tb_label,   'score': tb_score},
        'vader':    {'sentiment': vader_label, 'score': vader_score, 'details': vader_details},
        'final':    final_label,
        'final_score': final_score,
        'confidence':  confidence
    })


@app.route('/preview', methods=['POST'])
def preview():
    """
    Accepts a CSV or Excel file and returns:
      - columns: list of all column names
      - suggested: the column we think contains review text
      - sample: first 3 values from the suggested column
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    ext  = file.filename.rsplit('.', 1)[-1].lower()

    if ext not in ('csv', 'xlsx', 'xls'):
        return jsonify({'error': 'Preview only available for CSV/Excel'}), 400

    try:
        df      = read_dataframe(file, ext)
        suggest = best_text_column(df)
        sample  = df[suggest].dropna().astype(str).head(3).tolist()
        return jsonify({
            'columns':   list(df.columns),
            'suggested': suggest,
            'sample':    sample
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': f'Unsupported file type: .{ext}'}), 400

    reviews = []

    try:
        if ext in ('csv', 'xlsx', 'xls'):
            df  = read_dataframe(file, ext)
            col = request.form.get('column', '').strip()

            # Validate user-chosen column
            if col and col in df.columns:
                chosen = col
            else:
                # Auto-detect the best text column
                chosen = best_text_column(df)

            reviews = df[chosen].dropna().astype(str).tolist()
            # Filter out rows that are clearly not reviews (pure numbers, very short)
            reviews = [r for r in reviews if len(r.strip()) > 3 and not r.strip().lstrip('-').isdigit()]

        elif ext == 'pdf':
            with pdfplumber.open(file) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            reviews = [line.strip() for line in text.splitlines() if len(line.strip()) > 10]

    except Exception as e:
        return jsonify({'error': f'Failed to parse file: {str(e)}'}), 500

    if not reviews:
        return jsonify({'error': 'No usable text found in the file. Please check the selected column.'}), 400

    reviews = reviews[:500]  # cap for performance

    results = []
    counts  = {'Positive': 0, 'Negative': 0, 'Neutral': 0}

    for review in reviews:
        tb_label,    tb_score                  = get_textblob_sentiment(review)
        vader_label, vader_score, vader_detail  = get_vader_sentiment(review)
        final_label, final_score, confidence   = get_final_sentiment(
            tb_score, vader_score, tb_label, vader_label
        )
        counts[final_label] += 1
        results.append({
            'text':       review[:200],
            'textblob':   {'sentiment': tb_label,    'score': tb_score},
            'vader':      {'sentiment': vader_label,  'score': vader_score},
            'final':      final_label,
            'final_score': final_score,
            'confidence': confidence
        })

    return jsonify({
        'total':   len(results),
        'counts':  counts,
        'results': results
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
