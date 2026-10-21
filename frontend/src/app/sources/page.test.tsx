import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import SourcesPage from "./page";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows the actual imported source count from the API", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ sources: [
    { id: "fixture", name: "測試資料集", period: "2026", status: "success", record_count: 6, last_synced_at: null },
  ] }) }));
  render(<SourcesPage />);
  expect(await screen.findByText("測試資料集")).toBeInTheDocument();
  expect(screen.getByText("6")).toBeInTheDocument();
});
