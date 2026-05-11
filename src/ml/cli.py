import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.ml.scoring import calculate_composite_score, generate_insight


def parse_args():
    parser = argparse.ArgumentParser(description='Python ML scoring CLI')
    parser.add_argument('--momentum', type=float, default=0.0, help='Momentum score')
    parser.add_argument('--volume', type=float, default=0.0, help='Volume signal score')
    parser.add_argument('--sentiment', type=float, default=0.0, help='Sentiment value between -1 and 1')
    parser.add_argument('--price-change', type=float, default=0.0, help='Recent price change percent')
    return parser.parse_args()


def main():
    args = parse_args()
    score = calculate_composite_score(args.momentum, args.volume, args.sentiment)
    insight = generate_insight(score, args.sentiment, args.momentum, args.price_change)
    
    result = {
        'score': round(score, 2),
        'insight': insight,
    }
    print(json.dumps(result))


if __name__ == '__main__':
    main()
