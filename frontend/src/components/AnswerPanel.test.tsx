import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnswerPanel } from "./AnswerPanel";

describe("AnswerPanel", () => {
  it("shows limitations, insufficient samples and linked page citations", () => {
    render(<AnswerPanel result={{ answer: "找到相關資料", cases: [], limitations: ["缺少規格"], sync_metadata: { status: "ready" },
      price_reference: { sample_count: 3, insufficient_sample: true, case_ids: [] },
      citations: [{ evidence_id: "chunk:1", source_url: "https://example.test/manual", page_number: 2 }] }}/>);
    expect(screen.getByText(/樣本不足/)).toBeInTheDocument();
    expect(screen.getByText("缺少規格")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /第 2 頁/ })).toHaveAttribute("href", "https://example.test/manual");
  });
});
