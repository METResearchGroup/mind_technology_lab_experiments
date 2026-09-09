export type LengthConfig = {
  rMin: number
  rMax: number
  lambdaShort: number
  lambdaLong: number
  penaltyCap: number
}

export const CHAT_LENGTH: LengthConfig = {
  rMin: 0.6,
  rMax: 1.4,
  lambdaShort: 0.4,
  lambdaLong: 0.2,
  penaltyCap: 0.4,
}

export const REDDIT_LENGTH: LengthConfig = {
  rMin: 0.8,
  rMax: 1.1,
  lambdaShort: 0.45,
  lambdaLong: 0.15,
  penaltyCap: 0.25,
}

const WORD_RE = /\b[\w']+\b/g
const CONTENT_RE = /[a-z0-9']+/g

const ASSISTANT_MARKERS = [
  "i'd be happy to",
  "i would be happy to",
  "as an ai",
  "great question",
  "i can help",
  "here are a few",
  "here are some",
  "let me know if",
  "happy to help",
  "of course!",
  "certainly",
  "i'm here to",
]

const HEDGES = [
  "perhaps",
  "it might",
  "it could",
  "one might",
  "generally speaking",
]

export type StyleProfile = {
  meanWords: number
  contractionRate: number
  firstPersonRate: number
  hedgeRate: number
  quirks: string[]
}

export function wordCount(text: string): number {
  return (text.match(WORD_RE) ?? []).length
}

export function contentTokens(text: string): string[] {
  return text.toLowerCase().match(CONTENT_RE) ?? []
}

export function lengthConfigForDomain(domain: string): LengthConfig {
  return domain === "chat" ? CHAT_LENGTH : REDDIT_LENGTH
}

export function clipTuringJudgeScore(score: number): number {
  return Math.min(score, 5)
}

export function turingReward(score: number): number {
  return (clipTuringJudgeScore(score) - 1) / 6
}

export function lengthPenalty(
  response: string,
  groundTruth: string,
  config: LengthConfig
): number {
  const generated = wordCount(response)
  const human = Math.max(wordCount(groundTruth), 1)
  const ratio = generated / human
  const vShort = Math.max((config.rMin - ratio) / config.rMin, 0)
  const vLong = Math.max((ratio - config.rMax) / config.rMax, 0)
  return Math.min(
    config.lambdaShort * vShort + config.lambdaLong * vLong,
    config.penaltyCap
  )
}

export function combineTuringReward(
  score: number,
  response: string,
  groundTruth: string,
  config: LengthConfig
): number {
  return Math.max(
    0,
    turingReward(score) - lengthPenalty(response, groundTruth, config)
  )
}

export function tokenF1(response: string, groundTruth: string): number {
  const pred = new Set(contentTokens(response))
  const gold = new Set(contentTokens(groundTruth))
  if (pred.size === 0 && gold.size === 0) return 1
  if (pred.size === 0 || gold.size === 0) return 0
  let overlap = 0
  for (const token of pred) {
    if (gold.has(token)) overlap += 1
  }
  const precision = overlap / pred.size
  const recall = overlap / gold.size
  if (precision + recall === 0) return 0
  return (2 * precision * recall) / (precision + recall)
}

export function meanGtLogprob(response: string, groundTruth: string): number {
  const responseTokens = contentTokens(response)
  const goldTokens = contentTokens(groundTruth)
  if (goldTokens.length === 0) return 0
  if (responseTokens.length === 0) return -8
  const counts = new Map<string, number>()
  for (const token of responseTokens) {
    counts.set(token, (counts.get(token) ?? 0) + 1)
  }
  const vocab = counts.size
  const total = responseTokens.length
  let logMass = 0
  for (const token of goldTokens) {
    const prob = ((counts.get(token) ?? 0) + 1) / (total + vocab + 1)
    logMass += Math.log(prob)
  }
  return Math.max(-8, Math.min(0, logMass / goldTokens.length))
}

export function profileText(text: string, quirks: string[] = []): StyleProfile {
  const tokens = contentTokens(text)
  const n = Math.max(tokens.length, 1)
  const contractions = text.match(/\b\w+'\w+\b/g) ?? []
  const firstPerson = text.match(/\b(i|i'm|i've|my|me)\b/gi) ?? []
  const lowered = text.toLowerCase()
  const hedges = HEDGES.reduce(
    (sum, word) => sum + (lowered.split(word).length - 1),
    0
  )
  return {
    meanWords: wordCount(text),
    contractionRate: contractions.length / n,
    firstPersonRate: firstPerson.length / n,
    hedgeRate: hedges / n,
    quirks,
  }
}

function assistantPenalty(text: string): number {
  const lowered = text.toLowerCase()
  let hits = ASSISTANT_MARKERS.filter((marker) => lowered.includes(marker)).length
  if (text.includes("1.") && text.includes("2.")) hits += 1
  return Math.min(2.5, hits * 0.9)
}

function quirkBonus(text: string, quirks: string[]): number {
  const lowered = text.toLowerCase()
  const hits = quirks.filter((quirk) => lowered.includes(quirk.toLowerCase())).length
  return Math.min(1.5, hits * 0.75)
}

export function turingLikert(
  response: string,
  groundTruth: string,
  historyProfile: StyleProfile
): number {
  let score = 4
  const responseProfile = profileText(response, historyProfile.quirks)
  const lengthGap = Math.abs(responseProfile.meanWords - historyProfile.meanWords)
  score -= Math.min(1.5, lengthGap / Math.max(historyProfile.meanWords, 1))
  score -= 1.2 * Math.abs(responseProfile.contractionRate - historyProfile.contractionRate)
  score -= 0.8 * Math.abs(responseProfile.firstPersonRate - historyProfile.firstPersonRate)
  score -= 0.6 * Math.abs(responseProfile.hedgeRate - historyProfile.hedgeRate)
  score -= assistantPenalty(response)
  score += quirkBonus(response, historyProfile.quirks)
  score += 0.4 * tokenF1(response, groundTruth)
  return Math.max(1, Math.min(7, score))
}

export function softmax(logits: number[]): number[] {
  const maximum = Math.max(...logits)
  const shifted = logits.map((value) => Math.exp(value - maximum))
  const total = shifted.reduce((sum, value) => sum + value, 0)
  return shifted.map((value) => value / total)
}

export function groupAdvantages(rewards: number[], eps = 1e-8): number[] {
  const n = rewards.length
  if (n === 0) return []
  const mean = rewards.reduce((sum, value) => sum + value, 0) / n
  const variance =
    rewards.reduce((sum, value) => sum + (value - mean) ** 2, 0) / n
  const std = Math.sqrt(variance)
  if (std < eps) return rewards.map(() => 0)
  return rewards.map((value) => (value - mean) / std)
}

export function updateLogits(
  logits: number[],
  actions: number[],
  advantages: number[],
  learningRate: number,
  klCoefficient: number,
  referenceLogits: number[]
): number[] {
  const updated = [...logits]
  const probabilities = softmax(updated)
  const grads = updated.map(() => 0)
  for (let i = 0; i < actions.length; i += 1) {
    const action = actions[i]
    const advantage = advantages[i]
    for (let index = 0; index < updated.length; index += 1) {
      const indicator = index === action ? 1 : 0
      grads[index] += advantage * (indicator - probabilities[index])
    }
  }
  const groupSize = Math.max(actions.length, 1)
  for (let index = 0; index < updated.length; index += 1) {
    updated[index] += learningRate * (grads[index] / groupSize)
  }
  if (klCoefficient > 0) {
    const current = softmax(updated)
    const reference = softmax(referenceLogits)
    for (let index = 0; index < updated.length; index += 1) {
      updated[index] -= klCoefficient * (current[index] - reference[index])
    }
  }
  return updated
}

export type Method = "turing" | "sim" | "logprob"

export function scoreResponse(
  method: Method,
  response: string,
  groundTruth: string,
  domain: string,
  historyProfile: StyleProfile
): {
  turingLikert: number
  turingReward: number
  lengthPenalty: number
  similarity: number
  logprob: number
  trainingReward: number
} {
  const config = lengthConfigForDomain(domain)
  const likert = turingLikert(response, groundTruth, historyProfile)
  const mapped = turingReward(likert)
  const penalty = lengthPenalty(response, groundTruth, config)
  const similarity = tokenF1(response, groundTruth)
  const logprob = meanGtLogprob(response, groundTruth)
  let trainingReward = mapped
  if (method === "turing") trainingReward = Math.max(0, mapped - penalty)
  if (method === "sim") trainingReward = similarity
  if (method === "logprob") trainingReward = logprob
  return {
    turingLikert: likert,
    turingReward: mapped,
    lengthPenalty: penalty,
    similarity,
    logprob,
    trainingReward,
  }
}
