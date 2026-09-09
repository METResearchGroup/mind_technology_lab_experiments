"use client"

import { useMemo, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts"

import hfJob from "@/data/hf_job.json"
import results from "@/data/mini_replication.json"
import { EXAMPLES } from "@/lib/examples"
import {
  scoreResponse,
  type Method,
} from "@/lib/turing-math"
import { trainPolicy } from "@/lib/train-policy"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

const winConfig = {
  chat: { label: "Chat", color: "var(--chart-2)" },
  reddit: { label: "Reddit", color: "var(--chart-4)" },
} satisfies ChartConfig

const turingConfig = {
  chat: { label: "Chat Turing score", color: "var(--chart-2)" },
  reddit: { label: "Reddit Turing score", color: "var(--chart-4)" },
} satisfies ChartConfig

const replicaConfig = {
  turing: { label: "Turing-RL", color: "var(--chart-2)" },
  sim: { label: "Sim-RL", color: "var(--chart-3)" },
  logprob: { label: "Logprob-RL", color: "var(--chart-4)" },
} satisfies ChartConfig

const methodLabels: Record<Method, string> = {
  turing: "Turing-RL",
  sim: "Sim-RL",
  logprob: "Logprob-RL",
}

function pct(value: number): string {
  return `${(value * 100).toFixed(0)}%`
}

function fmt(value: number, digits = 2): string {
  return value.toFixed(digits)
}

export function DashboardApp() {
  const winData = [
    {
      method: "SFT-Init",
      chat: results.paper.human_win_rates.chat["SFT-Init"].mean,
      reddit: results.paper.human_win_rates.reddit["SFT-Init"].mean,
    },
    {
      method: "Sim-RL",
      chat: results.paper.human_win_rates.chat["Sim-RL"].mean,
      reddit: results.paper.human_win_rates.reddit["Sim-RL"].mean,
    },
    {
      method: "Turing-RL",
      chat: results.paper.human_win_rates.chat["Turing-RL"].mean,
      reddit: results.paper.human_win_rates.reddit["Turing-RL"].mean,
    },
  ]

  const ablationData = [
    {
      representation: "History + persona",
      chat: results.paper.turing_rl_ablation.chat.history_persona.turing,
      reddit: results.paper.turing_rl_ablation.reddit.history_persona.turing,
    },
    {
      representation: "History only",
      chat: results.paper.turing_rl_ablation.chat.history.turing,
      reddit: results.paper.turing_rl_ablation.reddit.history.turing,
    },
    {
      representation: "Persona only",
      chat: results.paper.turing_rl_ablation.chat.persona.turing,
      reddit: results.paper.turing_rl_ablation.reddit.persona.turing,
    },
  ]

  const replicaRows = results.replica.summary
  const replicaChart = EXAMPLES.map((example) => {
    const rowFor = (method: Method) =>
      replicaRows.find(
        (row) =>
          row.example_id === example.exampleId && row.method === method
      )
    return {
      user: example.userName,
      turing: rowFor("turing")?.human_like_prob ?? 0,
      sim: rowFor("sim")?.human_like_prob ?? 0,
      logprob: rowFor("logprob")?.human_like_prob ?? 0,
    }
  })

  return (
    <div className="min-h-svh bg-background">
      <header className="border-b">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-6 sm:px-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">arXiv 2606.19336</Badge>
            <Badge variant="outline">OpenReview 08Z5or1Jys</Badge>
            <Badge variant="outline">Dummy-data replica</Badge>
          </div>
          <h1 className="font-heading text-2xl font-medium tracking-tight">
            Learning User Simulators with Turing Rewards
          </h1>
          <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
            Wang, Zhang, Qiu, He, Li, Pentland, Levy, and Kim train a language
            model to play the user, not the assistant. The usual signal copies
            one ground-truth reply. Turing-RL instead asks a judge which reply
            is more likely from the real user, then trains with GRPO.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              nativeButton={false}
              render={
                <a
                  href="https://arxiv.org/abs/2606.19336"
                  target="_blank"
                  rel="noreferrer"
                />
              }
            >
              Paper
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={
                <a
                  href="https://github.com/SusanWYS/turing-rl"
                  target="_blank"
                  rel="noreferrer"
                />
              }
            >
              Official code
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={
                <a
                  href="https://huggingface.co/Qwen/Qwen3-8B"
                  target="_blank"
                  rel="noreferrer"
                />
              }
            >
              Qwen3-8B
            </Button>
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-8 sm:px-6">
        <section className="grid gap-4 md:grid-cols-3">
          <Takeaway
            title="Indistinguishability, not copying"
            body="A person can say many true things in the same context. The paper trains for replies that a judge cannot tell apart from that person, rather than for overlap with one recorded sentence."
          />
          <Takeaway
            title="A capped 1 to 7 Turing reward"
            body="The judge scores 1 if the human reply looks more real and 7 if the model reply does. Training uses (min(s, 5) − 1) / 6. The cap at 5 stops the model from being rewarded for sounding more human than the human."
          />
          <Takeaway
            title="Chat is where the gap is largest"
            body="Human annotators chose Turing-RL over real chat replies 57% of the time, against about 50% for SFT and Sim-RL. On Reddit, Turing-RL and Sim-RL are both near chance, and both beat SFT."
          />
        </section>

        <Alert>
          <AlertTitle>Paper scale vs this replica</AlertTitle>
          <AlertDescription>
            The paper trains Qwen3-8B with LoRA GRPO for about 1680 GPU hours
            and uses Qwen3.5-397B as the training judge. This dashboard still
            includes the dummy softmax replica. The Qwen3-8B tab tracks a
            scaled Hugging Face Jobs run: LoRA SFT then GRPO on Qwen/Qwen3-8B,
            with gpt-4o-mini substituting for the 397B OpenRouter judge.
          </AlertDescription>
        </Alert>

        <Tabs defaultValue="paper">
          <TabsList>
            <TabsTrigger value="paper">Paper results</TabsTrigger>
            <TabsTrigger value="replica">Dummy replica</TabsTrigger>
            <TabsTrigger value="qwen">Qwen3-8B job</TabsTrigger>
            <TabsTrigger value="playground">Interactive judge</TabsTrigger>
          </TabsList>

          <TabsContent value="paper" className="flex flex-col gap-4 pt-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>Human Turing test win rate</CardTitle>
                  <CardDescription>
                    Fraction of times annotators picked the model reply over
                    the real user. Chance is 0.50. Source: Table 1.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer config={winConfig} className="h-64 w-full">
                    <BarChart data={winData} accessibilityLayer>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="method" tickLine={false} axisLine={false} />
                      <YAxis
                        domain={[0.3, 0.7]}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(value) => pct(Number(value))}
                      />
                      <ChartTooltip
                        content={
                          <ChartTooltipContent
                            formatter={(value) => pct(Number(value))}
                          />
                        }
                      />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Bar dataKey="chat" fill="var(--color-chat)" radius={4} />
                      <Bar
                        dataKey="reddit"
                        fill="var(--color-reddit)"
                        radius={4}
                      />
                    </BarChart>
                  </ChartContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Turing-RL user representation</CardTitle>
                  <CardDescription>
                    Mean Turing judge score on a 1 to 7 scale for history,
                    persona, or both. Source: Table 2.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ChartContainer config={turingConfig} className="h-64 w-full">
                    <BarChart data={ablationData} accessibilityLayer>
                      <CartesianGrid vertical={false} />
                      <XAxis
                        dataKey="representation"
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        domain={[3, 5]}
                        tickLine={false}
                        axisLine={false}
                      />
                      <ChartTooltip content={<ChartTooltipContent />} />
                      <ChartLegend content={<ChartLegendContent />} />
                      <Bar dataKey="chat" fill="var(--color-chat)" radius={4} />
                      <Bar
                        dataKey="reddit"
                        fill="var(--color-reddit)"
                        radius={4}
                      />
                    </BarChart>
                  </ChartContainer>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>What the paper actually trains</CardTitle>
                <CardDescription>
                  SFT on user replies with a thinking trace, then GRPO with
                  four samples per prompt.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm leading-relaxed">
                <p>
                  Each example has a reserved history block h, an optional
                  induced persona ρ, the current context x, and the held-out
                  user reply y*. The judge sees h, x, y*, and a model sample y,
                  with order randomized, then scores which one the real user
                  wrote.
                </p>
                <p className="font-mono text-xs">
                  r_turing = (min(s, 5) - 1) / 6, then subtract a length
                  penalty if the reply is much shorter or longer than y*.
                </p>
                <p>
                  Sim-RL instead scores content overlap with y*. Logprob-RL
                  scores the log probability of y* after the model writes a
                  thinking trace. Turing-RL matches Sim-RL on content overlap
                  while scoring higher on human-likeness.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="replica" className="flex flex-col gap-4 pt-4">
            <Card>
              <CardHeader>
                <CardTitle>Dummy GRPO: probability of the human-like reply</CardTitle>
                <CardDescription>
                  After 80 GRPO steps with group size 4. Turing-RL stays on
                  the human-like action. Logprob-RL on the Reddit user
                  collapses to the too-short action.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ChartContainer config={replicaConfig} className="h-64 w-full">
                  <BarChart data={replicaChart} accessibilityLayer>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="user" tickLine={false} axisLine={false} />
                    <YAxis
                      domain={[0, 1]}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => pct(Number(value))}
                    />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value) => pct(Number(value))}
                        />
                      }
                    />
                    <ChartLegend content={<ChartLegendContent />} />
                    <Bar dataKey="turing" fill="var(--color-turing)" radius={4} />
                    <Bar dataKey="sim" fill="var(--color-sim)" radius={4} />
                    <Bar
                      dataKey="logprob"
                      fill="var(--color-logprob)"
                      radius={4}
                    />
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Chosen action after dummy GRPO</CardTitle>
                <CardDescription>
                  Mode of the softmax policy. Human-like is the intended
                  user-style reply in the dummy catalog.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Domain</TableHead>
                      <TableHead>Method</TableHead>
                      <TableHead>Mode</TableHead>
                      <TableHead>P(human-like)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {replicaRows.map((row) => (
                      <TableRow
                        key={`${row.example_id}-${row.method}`}
                      >
                        <TableCell className="whitespace-normal">
                          {EXAMPLES.find(
                            (example) => example.exampleId === row.example_id
                          )?.userName ?? row.example_id}
                        </TableCell>
                        <TableCell>{row.domain}</TableCell>
                        <TableCell>
                          {methodLabels[row.method as Method]}
                        </TableCell>
                        <TableCell className="whitespace-normal">
                          {row.mode_kind.replaceAll("_", " ")}
                        </TableCell>
                        <TableCell>{pct(row.human_like_prob)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="qwen" className="flex flex-col gap-4 pt-4">
            <Card>
              <CardHeader>
                <CardTitle>Hugging Face Jobs: Qwen3-8B Turing-RL</CardTitle>
                <CardDescription>
                  Real LoRA SFT then GRPO on {hfJob.base_model}, submitted to
                  HF Jobs. This is a short slice, not the paper&apos;s 1680
                  GPU-hour training.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">{hfJob.status}</Badge>
                  <Badge variant="outline">{hfJob.flavor}</Badge>
                  <Badge variant="outline">{hfJob.timeout} timeout</Badge>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {hfJob.scale_note}
                </p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Field</TableHead>
                      <TableHead>Value</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell>Job ID</TableCell>
                      <TableCell className="font-mono text-xs">
                        {hfJob.job_id ?? "not submitted yet"}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Paper judge</TableCell>
                      <TableCell>{hfJob.paper_judge}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>This job&apos;s judge</TableCell>
                      <TableCell>
                        {hfJob.job_judge}. {hfJob.job_judge_reason}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>SFT adapter</TableCell>
                      <TableCell className="font-mono text-xs">
                        {hfJob.sft_repo}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>GRPO adapter</TableCell>
                      <TableCell className="font-mono text-xs">
                        {hfJob.grpo_repo}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Missing keys</TableCell>
                      <TableCell>
                        {hfJob.missing_keys.join(", ") || "none"}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
                <div className="flex flex-wrap gap-2">
                  {hfJob.job_url ? (
                    <Button
                      nativeButton={false}
                      render={
                        <a
                          href={hfJob.job_url}
                          target="_blank"
                          rel="noreferrer"
                        />
                      }
                    >
                      Job logs
                    </Button>
                  ) : null}
                  <Button
                    variant="outline"
                    nativeButton={false}
                    render={
                      <a
                        href={`https://huggingface.co/${hfJob.sft_repo}`}
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                  >
                    SFT repo
                  </Button>
                  <Button
                    variant="outline"
                    nativeButton={false}
                    render={
                      <a
                        href={`https://huggingface.co/${hfJob.grpo_repo}`}
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                  >
                    GRPO repo
                  </Button>
                  <Button
                    variant="outline"
                    nativeButton={false}
                    render={
                      <a
                        href={hfJob.trackio_url}
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                  >
                    Trackio
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="playground" className="pt-4">
            <Playground />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

function Takeaway({ title, body }: { title: string; body: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-muted-foreground">{body}</p>
      </CardContent>
    </Card>
  )
}

function Playground() {
  const [exampleId, setExampleId] = useState(EXAMPLES[0].exampleId)
  const [candidateId, setCandidateId] = useState(EXAMPLES[0].candidates[0].id)
  const [customText, setCustomText] = useState(EXAMPLES[0].candidates[0].text)
  const [method, setMethod] = useState<Method>("turing")
  const [policy, setPolicy] = useState<ReturnType<typeof trainPolicy> | null>(
    null
  )

  const example = EXAMPLES.find((item) => item.exampleId === exampleId) ?? EXAMPLES[0]

  const scores = useMemo(
    () =>
      scoreResponse(
        method,
        customText,
        example.groundTruth,
        example.domain,
        example.historyProfile
      ),
    [customText, example, method]
  )

  function handleUserChange(value: string | null) {
    if (!value) return
    const next = EXAMPLES.find((item) => item.exampleId === value) ?? EXAMPLES[0]
    setExampleId(next.exampleId)
    setCandidateId(next.candidates[0].id)
    setCustomText(next.candidates[0].text)
    setPolicy(null)
  }

  function handleCandidateChange(value: string | null) {
    if (!value) return
    const candidate = example.candidates.find((item) => item.id === value)
    if (!candidate) return
    setCandidateId(candidate.id)
    setCustomText(candidate.text)
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <CardHeader>
          <CardTitle>Score a reply the way Turing-RL does</CardTitle>
          <CardDescription>
            The judge here is a transparent heuristic, not Qwen3.5-397B. It
            penalizes assistant phrasing, rewards user quirks, and only gives
            a small bump for overlap with the ground truth.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="user">Dummy user</FieldLabel>
              <Select value={exampleId} onValueChange={handleUserChange}>
                <SelectTrigger id="user" className="w-full">
                  <SelectValue>
                    {example.userName} ({example.domain})
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {EXAMPLES.map((item) => (
                      <SelectItem key={item.exampleId} value={item.exampleId}>
                        {item.userName} ({item.domain})
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>

            <Field>
              <FieldLabel>Persona</FieldLabel>
              <p className="text-sm leading-relaxed">{example.persona}</p>
            </Field>

            <Field>
              <FieldLabel>History</FieldLabel>
              <ul className="flex flex-col gap-1 text-sm leading-relaxed">
                {example.history.map((line) => (
                  <li key={line} className="rounded-md bg-muted px-3 py-2">
                    {line}
                  </li>
                ))}
              </ul>
            </Field>

            <Field>
              <FieldLabel>Context</FieldLabel>
              <p className="text-sm leading-relaxed">{example.context}</p>
              <FieldDescription>Ground truth: {example.groundTruth}</FieldDescription>
            </Field>

            <Field>
              <FieldLabel htmlFor="catalog">Catalog reply</FieldLabel>
              <Select value={candidateId} onValueChange={handleCandidateChange}>
                <SelectTrigger id="catalog" className="w-full">
                  <SelectValue>
                    {example.candidates.find((item) => item.id === candidateId)
                      ?.label ?? candidateId}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {example.candidates.map((candidate) => (
                      <SelectItem key={candidate.id} value={candidate.id}>
                        {candidate.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </Field>

            <Field>
              <FieldLabel htmlFor="reply">Reply to score</FieldLabel>
              <Textarea
                id="reply"
                value={customText}
                onChange={(event) => setCustomText(event.target.value)}
                rows={5}
              />
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>

      <div className="flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Scores</CardTitle>
            <CardDescription>
              Turing mapping is (min(s, 5) − 1) / 6. Length penalty uses the
              paper&apos;s chat or Reddit band.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <ScoreTile label="Turing Likert" value={fmt(scores.turingLikert)} />
            <ScoreTile label="Turing reward" value={fmt(scores.turingReward)} />
            <ScoreTile
              label="Length penalty"
              value={fmt(scores.lengthPenalty)}
            />
            <ScoreTile
              label="Similarity F1"
              value={pct(scores.similarity)}
            />
            <ScoreTile label="Dummy logprob" value={fmt(scores.logprob)} />
            <ScoreTile
              label={`${methodLabels[method]} train reward`}
              value={fmt(scores.trainingReward)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Run dummy GRPO in the browser</CardTitle>
            <CardDescription>
              80 steps, 4 samples per step, softmax over the catalog. Custom
              typed text is scored above, but training still uses the five
              catalog actions.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <ToggleGroup
              value={[method]}
              onValueChange={(values) => {
                const next = values[0]
                if (next === "turing" || next === "sim" || next === "logprob") {
                  setMethod(next)
                  setPolicy(null)
                }
              }}
            >
              <ToggleGroupItem value="turing">Turing-RL</ToggleGroupItem>
              <ToggleGroupItem value="sim">Sim-RL</ToggleGroupItem>
              <ToggleGroupItem value="logprob">Logprob-RL</ToggleGroupItem>
            </ToggleGroup>
            <Button
              onClick={() => setPolicy(trainPolicy(example, method, 80, 7))}
            >
              Train 80 GRPO steps
            </Button>
            {policy ? (
              <div className="flex flex-col gap-3">
                <p className="text-sm">
                  Chosen action:{" "}
                  <span className="font-medium">
                    {policy.modeKind.replaceAll("_", " ")}
                  </span>
                </p>
                <div className="flex flex-col gap-2">
                  {example.candidates.map((candidate, index) => (
                    <div key={candidate.id} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-xs">
                        <span>{candidate.label}</span>
                        <span>{pct(policy.probabilities[index] ?? 0)}</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full bg-foreground"
                          style={{
                            width: `${Math.max(1, (policy.probabilities[index] ?? 0) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <Separator />
                <ChartContainer
                  config={{
                    humanLike: {
                      label: "P(human-like)",
                      color: "var(--chart-2)",
                    },
                  }}
                  className="h-40 w-full"
                >
                  <LineChart data={policy.curve} accessibilityLayer>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="step" tickLine={false} axisLine={false} />
                    <YAxis
                      domain={[0, 1]}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => pct(Number(value))}
                    />
                    <ChartTooltip
                      content={
                        <ChartTooltipContent
                          formatter={(value) => pct(Number(value))}
                        />
                      }
                    />
                    <Line
                      type="monotone"
                      dataKey="humanLike"
                      stroke="var(--color-humanLike)"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ChartContainer>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ScoreTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-muted px-3 py-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-sm">{value}</span>
    </div>
  )
}
