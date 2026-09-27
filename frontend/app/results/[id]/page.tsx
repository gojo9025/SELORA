import ResultsClient from "./ResultsClient";

export function generateStaticParams() {
  return [{ id: "view" }];
}

export default function ResultsPage() {
  return <ResultsClient />;
}
