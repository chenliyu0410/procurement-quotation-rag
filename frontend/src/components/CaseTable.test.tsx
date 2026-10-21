import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { CaseTable } from "./CaseTable";

it("keeps metro budget and reporting month distinct from missing award values", () => {
  render(<CaseTable cases={[{ id: "case:metro", title: "捷運設備", text: "設備", source_url: "https://data.taipei/",
    metadata: { agency: "捷運公司", budget_amount: "7599391.00", award_amount: null, source_period: "2026-10" } }]} />);
  expect(screen.getByRole("columnheader", { name: "預算金額" })).toBeInTheDocument();
  const row = screen.getByRole("row", { name: /捷運設備/ });
  expect(within(row).getByText("7599391.00")).toBeInTheDocument();
  expect(within(row).getByText("2026-10")).toBeInTheDocument();
  expect(within(row).getByText("未提供")).toBeInTheDocument();
});
