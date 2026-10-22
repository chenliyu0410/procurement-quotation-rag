import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryForm } from "./QueryForm";

describe("QueryForm", () => {
  it("blocks blanks and fills an example", () => {
    const onQuery = vi.fn(); render(<QueryForm onQuery={onQuery} loading={false}/>);
    expect(screen.getByRole("button", { name: "查詢公開資料" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "找捷運公司預算300萬到1000萬元的案件" }));
    expect(screen.getByLabelText("輸入採購問題")).toHaveValue("找捷運公司預算300萬到1000萬元的案件");
    fireEvent.click(screen.getByRole("button", { name: "查詢公開資料" }));
    expect(onQuery).toHaveBeenCalledWith("找捷運公司預算300萬到1000萬元的案件");
  });

  it("disables submission while loading", () => {
    render(<QueryForm onQuery={() => undefined} loading/>);
    expect(screen.getByRole("button", { name: "整理資料中…" })).toBeDisabled();
  });
});
