import { Suspense } from "react";
import AuditorClient from "./AuditorClient";

export default function AuditorPage() {
  return (
    <Suspense>
      <AuditorClient />
    </Suspense>
  );
}
