import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { BRDQAPanel } from "@/components/brd/BRDQAPanel"
import { askBRD } from "@/api/brd"

vi.mock("@/api/brd", () => ({ askBRD: vi.fn() }))

const askBRDMock = vi.mocked(askBRD)

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })

  return render(
    <QueryClientProvider client={client}>
      <BRDQAPanel workspaceId="ws-1" />
    </QueryClientProvider>,
  )
}

async function ask(question: string) {
  const user = userEvent.setup()

  await user.type(screen.getByPlaceholderText(/ask\.\.\./i), question)
  await user.click(screen.getByRole("button", { name: "Ask" }))
}

beforeEach(() => {
  askBRDMock.mockReset()
})

describe("BRDQAPanel", () => {
  it("shows the user's message before the request resolves", async () => {
    askBRDMock.mockReturnValue(new Promise(() => {}))

    renderPanel()
    await ask("What is the budget?")

    // The bubble is optimistic; the composer has already been cleared, so
    // this text can only be coming from the message list.
    expect(screen.getByText("What is the budget?")).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/ask\.\.\./i)).toHaveValue("")
    expect(screen.getByText("Thinking...")).toBeInTheDocument()
    expect(askBRDMock).toHaveBeenCalledWith("ws-1", "What is the budget?")
  })

  it("renders the answer paragraphs and its sources with the source type", async () => {
    askBRDMock.mockResolvedValue({
      answer: "First paragraph.\n\nSecond paragraph.",
      sources: [{ id: "doc-1", title: "Brief", source_type: "file" }],
    })

    renderPanel()
    await ask("Where did this come from?")

    await waitFor(() => {
      expect(screen.getByText("First paragraph.")).toBeInTheDocument()
    })

    expect(screen.getByText("Second paragraph.")).toBeInTheDocument()
    expect(screen.getByText("Brief")).toBeInTheDocument()
    expect(screen.getByText("file")).toBeInTheDocument()
    expect(screen.queryByText("Thinking...")).not.toBeInTheDocument()
  })

  it("rolls the bubble back and restores the composer when the request fails", async () => {
    askBRDMock.mockRejectedValue(new Error("network"))

    renderPanel()
    await ask("Will this fail?")

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Couldn't answer. Try again.",
      )
    })

    // The message is gone from the list, and the question is back in the
    // composer so the user can retry without retyping it. Scoped to `p`
    // because a textarea's value also matches text queries in jsdom.
    expect(
      screen.queryByText("Will this fail?", { selector: "p" }),
    ).not.toBeInTheDocument()
    expect(screen.getByPlaceholderText(/ask\.\.\./i)).toHaveValue(
      "Will this fail?",
    )
  })

  it("ignores an empty or whitespace-only question", async () => {
    renderPanel()

    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText(/ask\.\.\./i), "   ")

    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled()

    await user.click(screen.getByRole("button", { name: "Ask" }))
    expect(askBRDMock).not.toHaveBeenCalled()
  })

  it("stays disabled while a request is in flight, so one question is sent once", async () => {
    askBRDMock.mockReturnValue(new Promise(() => {}))

    renderPanel()
    await ask("Only once?")

    const askButton = screen.getByRole("button", { name: "Ask" })

    expect(askButton).toBeDisabled()
    expect(screen.getByPlaceholderText(/ask\.\.\./i)).toBeDisabled()

    await userEvent.setup().click(askButton)
    expect(askBRDMock).toHaveBeenCalledTimes(1)
  })

  it("clears the conversation on request", async () => {
    askBRDMock.mockResolvedValue({ answer: "An answer.", sources: [] })

    renderPanel()
    await ask("Anything?")

    await waitFor(() => {
      expect(screen.getByText("An answer.")).toBeInTheDocument()
    })

    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Clear Q&A" }))

    expect(screen.queryByText("An answer.")).not.toBeInTheDocument()
    expect(screen.queryByText("Anything?")).not.toBeInTheDocument()
    expect(
      screen.getByText(/ask about requirements, decisions/i),
    ).toBeInTheDocument()
  })
})
