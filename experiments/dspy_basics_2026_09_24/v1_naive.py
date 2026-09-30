"""Naive unoptimized irony classification."""

from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from shared.dataloader import load_tweets
from shared.label_classes import IronyClassification
from shared.scorer import Scorer

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

POSITIVE_LABEL = "irony"

classifier = ChatOpenAI(model="gpt-5.4-nano").with_structured_output(
    IronyClassification
)


def classify(text: str) -> IronyClassification:
    result = classifier.invoke(
        "Classify the tweet as ironic or not.\n\nTweet:\n" + text
    )
    if not isinstance(result, IronyClassification):
        raise TypeError(f"Expected IronyClassification, got {type(result).__name__}")
    return result


def _example(text: str, actual: str, predicted: str) -> str:
    return f"text: {text}, actual: {actual} predicted: {predicted}"


def _print_examples(title: str, examples: list[str]) -> None:
    print(title)
    print()
    for index, example in enumerate(examples, start=1):
        print(f"{index}. {example}")


def main() -> None:
    tweets = load_tweets(config="irony", split="test")
    subset = tweets.select(range(len(tweets) - 50, len(tweets)))
    label_names = list(tweets.features["label"].names)
    scorer = Scorer(label_names, POSITIVE_LABEL)
    correct: list[str] = []
    wrong: list[str] = []

    for row in subset:
        predicted = classify(row["text"])
        truth_id = int(row["label"])
        actual = label_names[truth_id]
        scorer.add(truth_id, predicted.label)
        example = _example(row["text"], actual, predicted.label)
        if predicted.label == actual and len(correct) < 5:
            correct.append(example)
        elif predicted.label != actual and len(wrong) < 5:
            wrong.append(example)

    metrics = scorer.score()
    print(
        "f1: {f1:.4f}, recall: {recall:.4f}, precision: {precision:.4f}, "
        "accuracy: {accuracy:.4f}".format(**metrics)
    )
    print()
    _print_examples("Examples that the model got right:", correct)
    print()
    _print_examples("Examples that the model got wrong:", wrong)


if __name__ == "__main__":
    main()
