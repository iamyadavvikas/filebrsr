import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import DemoClient from "./DemoClient";

export const metadata = {
  title: "Live Demo — FileBRSR AI Extraction",
  description: "See a pre-filled BRSR extraction from a real annual report. No signup required.",
};

export default function DemoPage() {
  return (
    <>
      <Navbar />
      <DemoClient />
      <Footer />
    </>
  );
}
