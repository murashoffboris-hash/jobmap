import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Button from "./Button";

describe("Button — mobile WCAG compliance", () => {
  it("renders with variant class that gets mobile min-height via CSS", () => {
    const { container } = render(<Button variant="primary">OK</Button>);
    // btn-primary @apply btn, which gets min-height: 44px via mobile media query
    expect(container.firstChild).toHaveClass("btn-primary");
    expect(container.firstChild?.nodeName).toBe("BUTTON");
  });

  it("outline variant renders correctly", () => {
    const { container } = render(<Button variant="outline">OK</Button>);
    expect(container.firstChild).toHaveClass("btn-outline");
    expect(container.firstChild?.nodeName).toBe("BUTTON");
  });

  it("ghost variant renders correctly", () => {
    const { container } = render(<Button variant="ghost">OK</Button>);
    expect(container.firstChild).toHaveClass("btn-ghost");
    expect(container.firstChild?.nodeName).toBe("BUTTON");
  });

  it("fullWidth adds w-full class", () => {
    const { container } = render(<Button fullWidth>Full</Button>);
    expect(container.firstChild).toHaveClass("w-full");
  });

  it("size sm renders smaller button", () => {
    const { container } = render(<Button size="sm">Small</Button>);
    expect(container.firstChild).toHaveClass("px-3");
    expect(container.firstChild).toHaveClass("py-1.5");
  });

  it("all clickable elements are buttons with text", () => {
    render(<Button>Test button</Button>);
    const btn = screen.getByText("Test button");
    expect(btn.tagName).toBe("SPAN");
    // parent should be the button
    expect(btn.parentElement?.tagName).toBe("BUTTON");
  });
});
