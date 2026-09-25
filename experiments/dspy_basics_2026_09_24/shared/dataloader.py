"""Load TweetEval tweets."""

from datasets import Dataset, load_dataset

DATASET_ID = "cardiffnlp/tweet_eval"


def load_tweets(config: str = "irony", split: str = "test") -> Dataset:
    return load_dataset(DATASET_ID, config, split=split)
