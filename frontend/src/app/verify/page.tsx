import type { Metadata } from "next";
import VerifyClient from "./VerifyClient";

export const metadata: Metadata = {
  title: "Verify a Disclosure | FileBRSR",
  description:
    "Independently confirm that a FileBRSR-disclosed number is authentic, untampered, and traceable to its emission factor source. No login required.",
};

export default function VerifyPage() {
  return <VerifyClient />;
}
