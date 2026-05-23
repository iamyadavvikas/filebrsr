import AssessmentForm from "./AssessmentForm";

export default function AssessPage({ params }: { params: Promise<{ id: string }> }) {
  return <AssessmentForm paramsPromise={params} />;
}
