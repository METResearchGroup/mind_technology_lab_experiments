import argparse
import json
import re
import os
import subprocess
from datetime import datetime
from typing import List, Dict

from src.model_loader import load_qwen_15b
from src.concepts import get_concept_pairs
from src.act_vectors import build_concept_vectors
from src.score import score_text_against_concepts
from src.viz import plot_bar


def load_posts(jsonl_path: str) -> List[Dict]:
    # Handle relaxed file: JSON array with triple-quoted submission strings
    with open(jsonl_path, "r", encoding="utf-8") as f:
        txt = f.read()
    try:
        data = json.loads(txt)
        assert isinstance(data, list)
        return data
    except Exception:
        # Replace triple-quoted submission values with proper JSON strings
        def _repl(m: re.Match) -> str:
            prefix = m.group(1)
            body = m.group(2)
            # Normalize line endings and strip leading/trailing whitespace consistently
            normalized = body.replace("\r\n", "\n")
            return f'{prefix}{json.dumps(normalized)}'

        fixed = re.sub(r'("submission":\s*)"""([\s\S]*?)"""', _repl, txt, flags=re.DOTALL)
        data = json.loads(fixed)
        assert isinstance(data, list)
        return data


def build_input_text(post: Dict, question: str) -> str:
    submission = post.get("submission", "").strip()
    return f"Reddit Post:\n{submission}\n\nQuestion:\n{question}"

def get_git_commit_hash() -> str:
    try:
        # repo root is parent of this script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(script_dir, ".."))
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Compute concept activations for Reddit posts.")
    parser.add_argument(
        "--posts",
        default="mech_interp_reddit/SAMPLE_REDDIT_POSTS.jsonl",
        help="Path to Reddit posts JSON array file.",
    )
    parser.add_argument(
        "--question",
        default="When answering, which moral concepts are most pertinent here?",
        help="Question to pair with the post.",
    )
    parser.add_argument(
        "--outdir",
        default="mech_interp_reddit/output",
        help="Directory to write bar chart images.",
    )
    parser.add_argument(
        "--layers",
        default="-4,-3,-2,-1",
        help="Comma-separated layer indices relative to HF hidden_states (e.g., '-4,-3,-2,-1').",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="HF model name to use (override default for testing, e.g., 'sshleifer/tiny-gpt2').",
    )
    args = parser.parse_args()

    model, tokenizer, device = load_qwen_15b(model_name=args.model)
    # Parse desired layers, then constrain to available range [-n_layers, -1]
    desired_layers = [int(x) for x in args.layers.split(",")]
    n_layers = getattr(model.config, "num_hidden_layers", None)
    if isinstance(n_layers, int) and n_layers > 0:
        safe_layers = [li for li in desired_layers if (-n_layers) <= li <= -1]
        if not safe_layers:
            k = min(4, n_layers)
            safe_layers = [-(k - i) for i in range(k)]  # e.g., [-4,-3,-2,-1] or truncated
        layer_indices = safe_layers
    else:
        # Fallback: just use last layer
        layer_indices = [-1]

    concept_pairs = get_concept_pairs()
    concept_vectors = build_concept_vectors(model, tokenizer, device, concept_pairs, layer_indices)

    posts = load_posts(args.posts)
    # Output session directory
    timestamp = datetime.now().strftime("%Y_%m_%d-%H:%M:%S")
    session_dir = os.path.join(args.outdir, timestamp)
    os.makedirs(session_dir, exist_ok=True)
    meta_map = {}

    for idx, post in enumerate(posts):
        text = build_input_text(post, args.question)
        scores = score_text_against_concepts(model, tokenizer, device, text, concept_vectors, layer_indices)
        print(f"\nPost {idx}: {post.get('link', '')}")
        for k, v in scores.items():
            print(f"  {k:22s}: {v:.3f}")

        out_path = os.path.join(session_dir, f"activations_{idx}.png")
        plot_bar(scores, title=f"Relative Activations — Post {idx}", out_path=out_path)
        print(f"Saved: {out_path}")
        # Track mapping of activation index to comment_id
        meta_map[str(idx)] = post.get("comment_id", "")

    # Write metadata.json
    metadata = {
        "timestamp": timestamp,
        "model": getattr(model, "name_or_path", args.model),
        "git_commit_hash": get_git_commit_hash(),
        "activation_id_to_comment_id": meta_map,
    }
    meta_path = os.path.join(session_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved: {meta_path}")


if __name__ == "__main__":
    main()


