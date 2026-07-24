import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Input from "./Input";

describe("Input", () => {
  it("renders with label", () => {
    render(<Input label="Email" />);
    expect(screen.getByText("Email")).toBeInTheDocument();
  });

  it("renders error message", () => {
    render(<Input label="Email" error="Required" />);
    expect(screen.getByText("Required")).toBeInTheDocument();
  });

  it("renders hint text", () => {
    render(<Input label="Email" hint="Enter your email" />);
    expect(screen.getByText("Enter your email")).toBeInTheDocument();
  });

  it("calls onChange when typed via data-testid", () => {
    const handleChange = vi.fn();
    render(<Input label="Name" onChange={handleChange} data-testid="name-input" />);
    const input = screen.getByTestId("name-input");
    fireEvent.change(input, { target: { value: "John" } });
    expect(handleChange).toHaveBeenCalled();
  });

  it("forwards ref", () => {
    const ref = { current: null };
    render(<Input label="Test" ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });
});
