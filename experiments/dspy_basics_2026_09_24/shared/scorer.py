"""Binary classification metrics."""


class Scorer:
    """Binary accuracy, precision, recall, and F1 for one positive label."""

    def __init__(self, label_names: list[str], positive_label: str) -> None:
        self.label_names = label_names
        self.positive = label_names.index(positive_label)
        self.y_true: list[int] = []
        self.y_pred: list[int] = []

    def add(self, truth_id: int, predicted_label: str) -> None:
        self.y_true.append(truth_id)
        self.y_pred.append(self.label_names.index(predicted_label))

    def score(self) -> dict[str, float]:
        true_positive = false_positive = false_negative = true_negative = 0
        for truth, pred in zip(self.y_true, self.y_pred, strict=True):
            if pred == self.positive and truth == self.positive:
                true_positive += 1
            elif pred == self.positive:
                false_positive += 1
            elif truth == self.positive:
                false_negative += 1
            else:
                true_negative += 1
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall) if precision + recall else 0.0
        )
        accuracy = (true_positive + true_negative) / len(self.y_true)
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
