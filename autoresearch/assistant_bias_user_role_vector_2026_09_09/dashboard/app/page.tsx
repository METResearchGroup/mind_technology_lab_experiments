import { Charts } from "@/components/Charts";
import { SteeringLab } from "@/components/SteeringLab";
import paper from "@/public/data/paper_results.json";
import mini from "@/public/data/mini_replication.json";
import { qwen } from "@/lib/qwen";

export default function Page() {
  return (
    <main id="main" className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-8 md:px-6 md:py-12">
      <header className="flex flex-col gap-4 border-b border-[var(--line)] pb-8">
        <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
          arXiv:2609.00608 · mini-replication dashboard
        </p>
        <h1 className="max-w-4xl text-4xl leading-tight md:text-5xl">
          {paper.citation.title}
        </h1>
        <p className="max-w-3xl text-lg text-[var(--muted)]">
          LLM user simulators stay helpful and keep going after a real person
          would leave. Jeong et al. show that this assistant bias sits in a
          measurable direction in the model’s hidden states, and that pushing
          along that direction changes how the simulator writes and when it
          quits.
        </p>
        <div className="flex flex-wrap gap-3 text-sm">
          <a
            className="rounded-full border border-[var(--line)] px-3 py-1.5 hover:border-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            href={paper.citation.url}
          >
            Paper on arXiv
          </a>
          <a
            className="rounded-full border border-[var(--line)] px-3 py-1.5 hover:border-[var(--accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            href="https://www.alphaxiv.org/abs/2609.00608"
          >
            alphaXiv page
          </a>
          <span className="rounded-full border border-[var(--line)] px-3 py-1.5 text-[var(--muted)]">
            Paper model: {paper.citation.model_in_paper}
          </span>
        </div>
        <dl className="mt-2 grid gap-3 sm:grid-cols-3">
          {paper.table1_style_layer11.map((row) => (
            <div
              key={row.direction}
              className="rounded-xl border border-[var(--line)] px-4 py-3"
            >
              <dt className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">
                {row.direction} {row.alpha === 0 ? "α=0" : `α=${row.alpha}`}
              </dt>
              <dd className="tabular mt-1 font-mono text-3xl">{row.mean.toFixed(2)}</dd>
              <dd className="text-sm text-[var(--muted)]">mean user-likeness, layer 11</dd>
            </div>
          ))}
        </dl>
      </header>

      <aside className="panel border-[var(--accent)] p-4 md:p-5">
        <h2 className="text-xl">What this replica actually ran</h2>
        <p className="mt-2 max-w-3xl text-[var(--muted)]">
          Hugging Face Jobs loaded{" "}
          <span translate="no">{qwen.model}</span> on {qwen.gpu}. It built the
          three Appendix E.1 reflection prompts on {qwen.n_dialogues} hand-crafted
          chats, read layer {qwen.layer_index} at the first-response-token
          position, and steered first messages at five alphas. Mean projection
          onto the user vector is{" "}
          <span className="tabular font-mono text-[var(--ink)]">
            {qwen.user_mean_projection.toFixed(2)}
          </span>{" "}
          for user reflections and{" "}
          <span className="tabular font-mono text-[var(--ink)]">
            {qwen.assistant_mean_projection.toFixed(2)}
          </span>{" "}
          for assistant reflections. Lexical user-likeness peaks at α=0.2. This
          is not LMSYS-Chat-1M, GPT-5 Mini, or SimulatorArena. A separate CPU
          check on planted hidden states recovers cosine{" "}
          <span className="tabular font-mono text-[var(--ink)]">
            {mini.recovery_cosine.toFixed(3)}
          </span>
          .
        </p>
        <p className="mt-3 text-sm">
          <a
            className="underline decoration-[var(--line)] underline-offset-4 hover:decoration-[var(--accent)]"
            href={qwen.hub_url ?? "https://huggingface.co/datasets/mtorres98/assistant-bias-user-role-vector-qwen-run"}
          >
            Qwen run JSON on the Hub
          </a>
        </p>
      </aside>

      <section aria-labelledby="takeaways">
        <h2 id="takeaways" className="mb-4 text-3xl">
          Key takeaways
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          {paper.takeaways.map((item, index) => (
            <article key={item.title} className="panel flex flex-col gap-2 p-5">
              <p className="font-mono text-sm text-[var(--accent)]">
                0{index + 1}
              </p>
              <h3 className="text-xl">{item.title}</h3>
              <p className="text-[var(--muted)]">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <SteeringLab />

      <section className="flex flex-col gap-4">
        <h2 className="text-3xl">Graphs</h2>
        <p className="max-w-3xl text-[var(--muted)]">
          Charts labeled Qwen 3.5 4B are from the Hugging Face Jobs run. Unless
          a caption says mini-replication or Qwen, the numbers are from the
          paper. Reconstructed series are labeled as such.
        </p>
        <Charts />
      </section>

      <section className="panel p-5 md:p-6">
        <h2 className="text-3xl">Method, compressed</h2>
        <ol className="mt-4 flex flex-col gap-3 text-[var(--muted)]">
          <li>
            1. Sample user–assistant chats (LMSYS-Chat-1M, 2–50 turns, 30 per
            topic, 720 chats in the paper).
          </li>
          <li>
            2. Ask the model to write a one-paragraph reflection on the same
            chat from the user side and from the assistant side, using three
            prompt phrasings.
          </li>
          <li>
            3. Keep reflections that an LLM judge marks as strongly or weakly
            representing the assigned role.
          </li>
          <li>
            4. Read the hidden state at the first response token. Average
            user minus assistant across chats. That difference is the user
            role vector.
          </li>
          <li>
            5. At inference, add α times the hidden-state norm times the unit
            vector, at one mid layer, on every token.
          </li>
        </ol>
      </section>

      <footer className="border-t border-[var(--line)] pt-6 text-sm text-[var(--muted)]">
        Jeong, Lee, Choi, van der Ben, and Kim, 2026. Qwen 3.5 4B ran on
        Hugging Face Jobs. The CPU check uses planted activations.
      </footer>
    </main>
  );
}
