import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Button from "./Button";

describe("Button", () => {
  it("renders children", () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText("Click me")).toBeInTheDocument();
  });

  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(screen.getByText("Click"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("applies variant classes", () => {
    const { container } = render(<Button variant="ghost">Ghost</Button>);
    expect(container.firstChild).toHaveClass("btn-ghost");
  });

  it("disables the button", () => {
    render(<Button disabled>Disabled</Button>);
    const btn = screen.getByText("Disabled").closest("button");
    expect(btn).toBeDisabled();
  });

  it("shows loading state", () => {
    render(<Button loading>Loading</Button>);
    const btn = screen.getByText("Loading").closest("button");
    expect(btn).toBeDisabled();
  });
});
