from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_sentiment(text):
    # Initialize the VADER sentiment intensity analyzer
    analyzer = SentimentIntensityAnalyzer()
    
    # Get the sentiment score
    sentiment_score = analyzer.polarity_scores(text)
    
    # Extract sentiment and confidence
    compound_score = sentiment_score['compound']
    
    if compound_score >= 0.05:
        sentiment = "positive"
    elif compound_score <= -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Confidence level as the absolute value of the compound score
    confidence = round(abs(compound_score), 2)
    
    return {"sentiment": sentiment, "confidence": confidence}
