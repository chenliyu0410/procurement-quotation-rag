import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("introduces the assistant and provides a query starting point", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: "採購與報價知識助理" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("輸入採購問題")).toBeInTheDocument();
    expect(
      screen.getByText("找捷運公司預算300萬到1000萬元的案件"),
    ).toBeInTheDocument();
  });
});
