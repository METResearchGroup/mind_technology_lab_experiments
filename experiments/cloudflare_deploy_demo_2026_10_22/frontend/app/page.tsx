import { env } from "cloudflare:workers";
import { DemoPanel } from "./demo-panel";

export const dynamic = "force-dynamic";

export default function Home() {
  const apiBase = env.API_BASE_URL || "http://127.0.0.1:8787";

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto grid max-w-3xl gap-8">
        <div className="grid gap-3">
          <h1 className="text-3xl font-semibold">Cloudflare deploy demo</h1>
          <p className="text-lg leading-8 text-slate-700">
            This page runs as a Next.js app on a Cloudflare Worker. It reads the
            FastAPI Worker from the browser, and it saves notes through a server
            action so the write token stays on the Worker.
          </p>
        </div>
        <DemoPanel apiBase={apiBase} />
      </section>
    </main>
  );
}
