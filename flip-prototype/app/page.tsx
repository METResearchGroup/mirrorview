"use client";

import * as React from "react";
import { RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type Feedback = "up" | "down" | null;

type SubmissionContext = {
  id: string;
  created_at: string;
  input_text: string;
};

type FlipApiResponse = {
  flipped_text?: string;
  explanation?: string;
};

const EXPLANATION_COLLAPSE_THRESHOLD_CHARS = 400;

export default function Home() {
  const [inputText, setInputText] = React.useState("");
  const [flippedText, setFlippedText] = React.useState<string | null>(null);
  const [explanation, setExplanation] = React.useState<string | null>(null);
  const [isExplanationOpen, setIsExplanationOpen] = React.useState(true);
  const [feedback, setFeedback] = React.useState<Feedback>(null);
  const [customVersion, setCustomVersion] = React.useState("");
  const [submission, setSubmission] = React.useState<SubmissionContext | null>(null);
  const [isFlipping, setIsFlipping] = React.useState(false);

  const customTextareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  const canFlip = inputText.trim().length > 0;
  const canReset = inputText.trim() !== "" || flippedText !== null || explanation !== null;
  const showCustomVersion = feedback === "down";

  async function handleFlip() {
    const trimmed = inputText.trim();
    if (!trimmed) {
      toast.error("Paste some text to flip.");
      return;
    }

    const baseUrl = (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/$/, "");
    if (!baseUrl) {
      toast.error("Missing NEXT_PUBLIC_API_URL. Set it to your backend URL.");
      return;
    }

    try {
      setIsFlipping(true);
      const nextSubmission: SubmissionContext = {
        id: crypto.randomUUID(),
        created_at: new Date().toISOString(),
        input_text: trimmed,
      };
      setSubmission(nextSubmission);

      const res = await fetch(`${baseUrl}/generate_response`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed, submission: nextSubmission }),
      });

      if (!res.ok) {
        let detail = `Request failed (${res.status})`;
        try {
          const data = (await res.json()) as { detail?: string };
          if (typeof data?.detail === "string" && data.detail.trim()) detail = data.detail;
        } catch {
          // ignore json parse errors
        }
        toast.error(detail);
        return;
      }

      const data = (await res.json()) as FlipApiResponse;
      if (!data?.flipped_text) {
        toast.error("Backend returned no flipped_text.");
        return;
      }

      setFlippedText(data.flipped_text);
      const nextExplanation =
        typeof data.explanation === "string" && data.explanation.trim()
          ? data.explanation
          : null;
      setExplanation(nextExplanation);
      setIsExplanationOpen(
        nextExplanation !== null &&
          nextExplanation.length <= EXPLANATION_COLLAPSE_THRESHOLD_CHARS,
      );
      setFeedback(null);
      setCustomVersion("");
    } catch (e) {
      toast.error(`Failed to reach backend: ${(e as Error).message ?? String(e)}`);
    } finally {
      setIsFlipping(false);
    }
  }

  function handleReset() {
    setInputText("");
    setFlippedText(null);
    setExplanation(null);
    setIsExplanationOpen(true);
    setFeedback(null);
    setCustomVersion("");
    setSubmission(null);
  }

  function handleExplanationToggle(e: React.SyntheticEvent<HTMLDetailsElement>) {
    setIsExplanationOpen(e.currentTarget.open);
  }

  function handleThumbUp() {
    setFeedback("up");
    toast.success("Thanks — feedback recorded (mock).");
  }

  function handleThumbDown() {
    setFeedback("down");
    toast("Got it. Write your preferred version below.");

    // Defer focus until the textarea exists in the DOM.
    queueMicrotask(() => customTextareaRef.current?.focus());
  }

  function handleSubmitCustom() {
    const trimmed = customVersion.trim();
    if (!trimmed) {
      toast.error("Please write your version before submitting.");
      return;
    }

    // Frontend-only prototype: no network call.
    console.log("Custom version submitted (mock):", {
      submission,
      inputText,
      flippedText,
      customVersion: trimmed,
    });

    toast.success("Submitted (mock).");
  }

  return (
    <div className="min-h-dvh bg-muted/30">
      <main className="mx-auto w-full max-w-2xl px-4 py-10 sm:px-6 sm:py-14">
        <header className="mb-10 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-medium text-muted-foreground">
              MirrorView
            </div>
            {canReset && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleReset}
              >
                <RotateCcw aria-hidden="true" />
                Reset progress
              </Button>
            )}
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Flip a post (prototype)
          </h1>
          <p className="text-base leading-7 text-muted-foreground">
            Paste a post and we’ll generate a flipped version. This is{" "}
            <span className="font-medium text-foreground">powered by the backend</span>{" "}
            (configure <span className="font-mono">NEXT_PUBLIC_API_URL</span>).
          </p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>Text to flip</CardTitle>
            <CardDescription>
              Enter the text you’d like to flip.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label htmlFor="inputText" className="sr-only">
              Text to flip
            </Label>
            <Textarea
              id="inputText"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste your post here…"
              className="min-h-36 resize-y"
            />
          </CardContent>
          <CardFooter className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
            <Button onClick={handleFlip} disabled={!canFlip || isFlipping}>
              {isFlipping ? "Flipping…" : "Flip"}
            </Button>
            <div className="text-sm text-muted-foreground">
              Calls <span className="font-mono">POST /generate_response</span>.
            </div>
          </CardFooter>
        </Card>

        {flippedText !== null && (
          <div className="mt-8 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Flipped output</CardTitle>
                <CardDescription>
                  Review the output, then give a quick thumbs up or down.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="whitespace-pre-wrap rounded-lg border bg-background px-4 py-3 text-sm leading-6">
                  {flippedText}
                </div>
                {explanation !== null && (
                  <details
                    open={isExplanationOpen}
                    onToggle={handleExplanationToggle}
                    className="rounded-lg border bg-background"
                  >
                    <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium">
                      Explanation
                    </summary>
                    <div className="whitespace-pre-wrap border-t px-4 py-3 text-sm leading-6 text-muted-foreground">
                      {explanation}
                    </div>
                  </details>
                )}
              </CardContent>
              <CardFooter className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant={feedback === "up" ? "default" : "outline"}
                    size="icon"
                    onClick={handleThumbUp}
                    aria-label="Thumbs up"
                  >
                    <ThumbsUp className="h-4 w-4" />
                  </Button>
                  <Button
                    type="button"
                    variant={feedback === "down" ? "default" : "outline"}
                    size="icon"
                    onClick={handleThumbDown}
                    aria-label="Thumbs down"
                  >
                    <ThumbsDown className="h-4 w-4" />
                  </Button>
                </div>
                <div className="text-sm text-muted-foreground">
                  {feedback === "up" && "Thanks!"}
                  {feedback === "down" && "Tell us what you’d prefer."}
                  {feedback === null && "Feedback optional."}
                </div>
              </CardFooter>
            </Card>

            {showCustomVersion && (
              <Card>
                <CardHeader>
                  <CardTitle>Your version</CardTitle>
                  <CardDescription>
                    If the flip isn’t right, write your preferred version and
                    submit it.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Label htmlFor="customVersion" className="sr-only">
                    Your version
                  </Label>
                  <Textarea
                    id="customVersion"
                    ref={customTextareaRef}
                    value={customVersion}
                    onChange={(e) => setCustomVersion(e.target.value)}
                    placeholder="Write your version here…"
                    className="min-h-32 resize-y"
                  />
                </CardContent>
                <CardFooter className="flex items-center justify-between">
                  <Button
                    type="button"
                    onClick={handleSubmitCustom}
                    disabled={customVersion.trim().length === 0}
                  >
                    Submit
                  </Button>
                  <div className="text-sm text-muted-foreground">
                    Stored nowhere (mock).
                  </div>
                </CardFooter>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
