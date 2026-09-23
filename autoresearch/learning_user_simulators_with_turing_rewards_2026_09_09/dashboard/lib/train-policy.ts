import type { Method } from "@/lib/turing-math"
import {
  groupAdvantages,
  scoreResponse,
  softmax,
  updateLogits,
} from "@/lib/turing-math"
import type { Example } from "@/lib/examples"

export type TrainedPolicy = {
  probabilities: number[]
  modeKind: string
  curve: { step: number; humanLike: number }[]
}

function mulberry32(seed: number) {
  let t = seed >>> 0
  return () => {
    t += 0x6d2b79f5
    let r = Math.imul(t ^ (t >>> 15), 1 | t)
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r)
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296
  }
}

function sampleAction(probabilities: number[], random: () => number): number {
  const draw = random()
  let cumulative = 0
  for (let index = 0; index < probabilities.length; index += 1) {
    cumulative += probabilities[index]
    if (draw <= cumulative) return index
  }
  return probabilities.length - 1
}

export function trainPolicy(
  example: Example,
  method: Method,
  steps = 80,
  seed = 7
): TrainedPolicy {
  const random = mulberry32(seed)
  let logits = example.candidates.map(() => 0)
  const reference = [...logits]
  const rewards = example.candidates.map(
    (candidate) =>
      scoreResponse(
        method,
        candidate.text,
        example.groundTruth,
        example.domain,
        example.historyProfile
      ).trainingReward
  )
  const curve: { step: number; humanLike: number }[] = []
  const humanIndex = example.candidates.findIndex(
    (candidate) => candidate.kind === "human_like"
  )
  for (let step = 0; step < steps; step += 1) {
    const probabilities = softmax(logits)
    const actions = [0, 1, 2, 3].map(() => sampleAction(probabilities, random))
    const sampled = actions.map((action) => rewards[action])
    const advantages = groupAdvantages(sampled)
    logits = updateLogits(logits, actions, advantages, 0.35, 0.001, reference)
    if (step % 10 === 0 || step === steps - 1) {
      curve.push({
        step,
        humanLike: softmax(logits)[humanIndex] ?? 0,
      })
    }
  }
  const probabilities = softmax(logits)
  const modeIndex = probabilities.indexOf(Math.max(...probabilities))
  return {
    probabilities,
    modeKind: example.candidates[modeIndex]?.kind ?? "unknown",
    curve,
  }
}
