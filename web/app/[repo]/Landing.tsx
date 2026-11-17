"use client";

import { useParams, useRouter } from "next/navigation";
import AskNext from "../components/AskNext";
import Brief from "../components/Brief";
import { Loading, RepoHeading, TopBar } from "../components/Chrome";
import QuestionBox from "../components/QuestionBox";
import { useRepo, useSettings } from "../lib/hooks";

// The repo page: the explanation with the question box under it. Asking opens the ask page.
export default function Landing() {
  const name = useParams<{ repo: string }>().repo;
  const router = useRouter();
  const { repo, overview, flow, error } = useRepo(name);
  const [settings, setSettings, health] = useSettings();
  const go = (q: string) => router.push(`/${name}/ask?q=${encodeURIComponent(q)}`);

  return (
    <>
      <TopBar />
      {!repo || !overview ? <Loading error={error} /> : (
        <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
          <RepoHeading repo={repo} />
          <div className="mt-10"><Brief overview={overview} flow={flow} onPickFile={(f) => router.push(`/${name}/ask?file=${encodeURIComponent(f)}`)} /></div>

          <section className="mt-14 border-t border-rule pt-10">
            <h2 className="mb-3 text-xl font-semibold">Ask about this code</h2>
            <QuestionBox busy={false} settings={settings} onSettings={setSettings}
              backends={health?.backends ?? ["gemini"]} onAsk={go} />
            <div className="mt-8"><AskNext questions={overview.starter_questions} onAsk={go} title="Where to go next" /></div>
          </section>
        </main>
      )}
    </>
  );
}
