"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Loading } from "../../components/Chrome";
import Workspace from "../../components/Workspace";
import { useRepo, useSettings } from "../../lib/hooks";

// The ask page: questions and answers on the left, code on the right. The question lives in
// the address, so the back button and bookmarks work.
export default function Ask() {
  const name = useParams<{ repo: string }>().repo;
  const params = useSearchParams();
  const question = params.get("q") ?? undefined;
  const file = params.get("file") ?? undefined;
  const router = useRouter();
  const { repo, overview, flow, error } = useRepo(name);
  const [settings, setSettings, health] = useSettings();

  return (
    <div className="flex h-[100svh] flex-col">
      <header className="flex min-w-0 items-baseline gap-4 border-b border-rule px-4 py-2.5 sm:px-6">
        <Link href="/" className="text-lg font-semibold tracking-tight">repo-qa</Link>
        <Link href={`/${name}`} className="truncate font-mono text-sm text-graphite hover:text-ink">
          {repo?.title ?? name}
        </Link>
      </header>
      {!repo || !overview ? <Loading error={error} /> : (
        <div className="min-h-0 flex-1">
          <Workspace repo={name} overview={overview} flow={flow} initialFile={file} settings={settings} onSettings={setSettings}
            backends={health?.backends ?? ["gemini"]} initialQuestion={question}
            onAsked={(q) => router.replace(`/${name}/ask?q=${encodeURIComponent(q)}`, { scroll: false })} />
        </div>
      )}
    </div>
  );
}
