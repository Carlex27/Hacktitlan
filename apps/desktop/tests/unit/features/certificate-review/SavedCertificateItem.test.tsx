import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SavedCertificateItem } from "@/features/certificate-review/components/SavedCertificateItem";
import { es } from "@/lib/i18n";

describe("SavedCertificateItem", () => {
  it.each(["draft", "needs_review", "approved", "rejected"] as const)("shows %s with a text label and preserves unknown data", async (status) => {
    const onReview = vi.fn();
    render(<ul><SavedCertificateItem number="ACTA-42" manufacturer={null} date={null} status={status} onReview={onReview} /></ul>);
    expect(screen.getByText(es.workspace.status[status])).toBeInTheDocument();
    expect(screen.getAllByText(es.workspace.unknown, { exact: true })).toHaveLength(2);
    expect(screen.getByText(`${es.workspace.date}:`)).toHaveTextContent(`${es.workspace.date}: ${es.workspace.unknown}`);
    await userEvent.setup().click(screen.getByRole("button", { name: "Abrir acta" }));
    expect(onReview).toHaveBeenCalledOnce();
  });
});
