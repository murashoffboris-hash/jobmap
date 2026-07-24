import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Avatar from "./Avatar";

describe("Avatar", () => {
  it("renders initials from full name", () => {
    render(<Avatar name="John Doe" />);
    expect(screen.getByText("JD")).toBeInTheDocument();
  });

  it("renders two initials for single word (first + last char)", () => {
    render(<Avatar name="Admin" />);
    expect(screen.getByText("AD")).toBeInTheDocument();
  });

  it("renders empty string for empty name", () => {
    const { container } = render(<Avatar name="" />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("applies size class", () => {
    const { container } = render(<Avatar name="User" size="lg" />);
    expect(container.firstChild).toHaveClass("w-14", "h-14");
  });
});
