import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { CitationList } from "./CitationList";

it("opens the cited PDF page while preserving its download query parameters", () => {
  render(<CitationList citations={[{ evidence_id: "chunk:one", source_url: "https://example.org/Download.ashx?u=abc&icon=.pdf", page_number: 2 }]} />);
  expect(screen.getByRole("link")).toHaveAttribute("href", "https://example.org/Download.ashx?u=abc&icon=.pdf#page=2");
});
