import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("채팅 작업 화면을 기본 화면으로 보여준다", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "DocSearch AI" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("API Key")).toBeInTheDocument();
    expect(screen.getByLabelText("질문")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /질문 보내기/ }),
    ).toBeDisabled();
  });
});
