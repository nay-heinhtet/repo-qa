import RepoQA from "./components/RepoQA";

// The page itself is a server component that only renders the client app; all data comes from
// FastAPI in the browser (spec W5).
export default function Page() {
  return <RepoQA />;
}
