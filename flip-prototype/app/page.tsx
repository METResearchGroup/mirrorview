"use client";

import * as React from "react";
import { Loader2, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react";
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
  model_id: string;
};

type FlipApiResponse = {
  flipped_text?: string;
  explanation?: string;
};

type ModelOption = {
  model_id: string;
  display_name: string;
  provider: string;
};

type ModelCatalogResponse = {
  default_model_id: string;
  models: ModelOption[];
};

type Example = {
  id: string;
  title: string;
  input_text: string;
  tags?: string[];
};

type ExampleSuggestionsResponse = {
  examples: Example[];
};

const EXPLANATION_COLLAPSE_THRESHOLD_CHARS = 400;
const FALLBACK_MODEL_ID = "gpt-5-nano";

async function extractErrorMessage(res: Response, fallbackStatus: number): Promise<string> {
  let detail = `Request failed (${fallbackStatus})`;
  try {
    const data = (await res.json()) as {
      detail?: string;
      error?: { message?: string };
    };
    if (typeof data?.error?.message === "string" && data.error.message.trim()) {
      detail = data.error.message;
    } else if (typeof data?.detail === "string" && data.detail.trim()) {
      detail = data.detail;
    }
  } catch {
    // ignore json parse errors
  }
  return detail;
}

export default function Home() {
  const [inputText, setInputText] = React.useState("");
  const [flippedText, setFlippedText] = React.useState<string | null>(null);
  const [explanation, setExplanation] = React.useState<string | null>(null);
  const [isExplanationOpen, setIsExplanationOpen] = React.useState(true);
  const [feedback, setFeedback] = React.useState<Feedback>(null);
  const [customVersion, setCustomVersion] = React.useState("");
  const [submission, setSubmission] = React.useState<SubmissionContext | null>(null);
  const [isFlipping, setIsFlipping] = React.useState(false);
  const [isSubmittingThumb, setIsSubmittingThumb] = React.useState(false);
  const [modelOptions, setModelOptions] = React.useState<ModelOption[]>([]);
  const [selectedModelId, setSelectedModelId] = React.useState(FALLBACK_MODEL_ID);
  const [isLoadingModels, setIsLoadingModels] = React.useState(false);
  const [exampleSuggestions, setExampleSuggestions] = React.useState<Example[]>([]);
  const [isLoadingExamples, setIsLoadingExamples] = React.useState(false);
  const [isLoadingRandomExample, setIsLoadingRandomExample] = React.useState(false);

  const customTextareaRef = React.useRef<HTMLTextAreaElement | null>(null);

  const canFlip = inputText.trim().length > 0;
  const canReset = inputText.trim() !== "" || flippedText !== null || explanation !== null;
  const showCustomVersion = feedback === "down";
  const getBaseUrl = React.useCallback(
    () => (process.env.NEXT_PUBLIC_API_URL ?? "").trim().replace(/\/$/, ""),
    [],
  );

  const applyExample = React.useCallback(
    (example: Example) => {
      setInputText(example.input_text);
      setFlippedText(null);
      setExplanation(null);
      setIsExplanationOpen(true);
      setFeedback(null);
      setCustomVersion("");
      setSubmission(null);
    },
    [
      setInputText,
      setFlippedText,
      setExplanation,
      setIsExplanationOpen,
      setFeedback,
      setCustomVersion,
      setSubmission,
    ],
  );

  const loadExampleSuggestions = React.useCallback(async () => {
    const baseUrl = getBaseUrl();
    if (!baseUrl) {
      return;
    }

    setIsLoadingExamples(true);
    try {
      const res = await fetch(`${baseUrl}/examples/suggestions?count=3`);
      if (!res.ok) {
        return;
      }
      const data = (await res.json()) as ExampleSuggestionsResponse;
      setExampleSuggestions(Array.isArray(data?.examples) ? data.examples : []);
    } catch {
      // ignore — examples are optional
    } finally {
      setIsLoadingExamples(false);
    }
  }, [getBaseUrl]);

  React.useEffect(() => {
    loadExampleSuggestions();
  }, [loadExampleSuggestions]);

  const fetchRandomExample = React.useCallback(async () => {
    const baseUrl = getBaseUrl();
    if (!baseUrl) {
      toast.error("Service is not configured. Please try again later.");
      return;
    }

    setIsLoadingRandomExample(true);
    try {
      const params = new URLSearchParams();
      exampleSuggestions.forEach((example) => params.append("exclude_id", example.id));
      const query = params.toString();
      const url = `${baseUrl}/examples/random${query ? `?${query}` : ""}`;
      const res = await fetch(url);
      if (!res.ok) {
        toast.error(await extractErrorMessage(res, res.status));
        return;
      }
      const data = (await res.json()) as Example;
      if (data?.input_text) {
        applyExample(data);
      }
    } catch {
      toast.error("Could not load an example right now. Please try again.");
    } finally {
      setIsLoadingRandomExample(false);
    }
  }, [applyExample, exampleSuggestions, getBaseUrl]);

  React.useEffect(() => {
    async function loadModels() {
      const baseUrl = getBaseUrl();
      if (!baseUrl) return;

      setIsLoadingModels(true);
      try {
        const res = await fetch(`${baseUrl}/models`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });
        if (!res.ok) return;
        const data = (await res.json()) as ModelCatalogResponse;
        if (!Array.isArray(data.models) || data.models.length === 0) return;
        setModelOptions(data.models);
        setSelectedModelId(data.default_model_id || FALLBACK_MODEL_ID);
      } catch {
        // fallback model remains available even if catalog fetch fails
      } finally {
        setIsLoadingModels(false);
      }
    }

    loadModels();
  }, [getBaseUrl]);

  async function handleFlip() {
    const trimmed = inputText.trim();
    if (!trimmed) {
      toast.error("Paste some text to flip.");
      return;
    }

    const baseUrl = getBaseUrl();
    if (!baseUrl) {
      toast.error("Service is not configured. Please try again later.");
      return;
    }

    try {
      setIsFlipping(true);
      const nextSubmission: SubmissionContext = {
        id: crypto.randomUUID(),
        created_at: new Date().toISOString(),
        input_text: trimmed,
        model_id: selectedModelId,
      };
      setSubmission(nextSubmission);

      const res = await fetch(`${baseUrl}/generate_response`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: trimmed, submission: nextSubmission }),
      });

      if (!res.ok) {
        toast.error(await extractErrorMessage(res, res.status));
        return;
      }

      const data = (await res.json()) as FlipApiResponse;
      if (!data?.flipped_text) {
        toast.error("No result was returned. Please try again.");
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
    } catch {
      toast.error("Something went wrong. Please try again.");
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

  async function handleThumbUp() {
    if (isSubmittingThumb) return;
    if (!submission) {
      toast.error("No submission available. Please flip text first.");
      return;
    }

    const baseUrl = getBaseUrl();
    if (!baseUrl) {
      toast.error("Service is not configured. Please try again later.");
      return;
    }

    setIsSubmittingThumb(true);
    try {
      setFeedback("up");
      const res = await fetch(`${baseUrl}/feedback/thumb`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submission,
          vote: "up",
          voted_at: new Date().toISOString(),
        }),
      });

      if (!res.ok) {
        toast.error(await extractErrorMessage(res, res.status));
        setFeedback(null);
        return;
      }

      toast.success("Thanks — feedback recorded.");
    } catch {
      toast.error("Something went wrong. Please try again.");
      setFeedback(null);
    } finally {
      setIsSubmittingThumb(false);
    }
  }

  async function handleThumbDown() {
    if (isSubmittingThumb) return;
    if (!submission) {
      toast.error("No submission available. Please flip text first.");
      return;
    }

    const baseUrl = getBaseUrl();
    if (!baseUrl) {
      toast.error("Service is not configured. Please try again later.");
      return;
    }

    setIsSubmittingThumb(true);
    try {
      setFeedback("down");
      const res = await fetch(`${baseUrl}/feedback/thumb`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submission,
          vote: "down",
          voted_at: new Date().toISOString(),
        }),
      });

      if (!res.ok) {
        toast.error(await extractErrorMessage(res, res.status));
        setFeedback(null);
        return;
      }

      toast("Got it. Write your preferred version below.");

      // Defer focus until the textarea exists in the DOM.
      queueMicrotask(() => customTextareaRef.current?.focus());
    } catch {
      toast.error("Something went wrong. Please try again.");
      setFeedback(null);
    } finally {
      setIsSubmittingThumb(false);
    }
  }

  async function handleSubmitCustom() {
    const trimmed = customVersion.trim();
    if (!trimmed) {
      toast.error("Please write your version before submitting.");
      return;
    }

    if (!submission) {
      toast.error("No submission available. Please flip text first.");
      return;
    }

    const baseUrl = getBaseUrl();
    if (!baseUrl) {
      toast.error("Service is not configured. Please try again later.");
      return;
    }

    try {
      const res = await fetch(`${baseUrl}/feedback/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submission,
          edited_text: trimmed,
          edited_at: new Date().toISOString(),
        }),
      });

      if (!res.ok) {
        toast.error(await extractErrorMessage(res, res.status));
        return;
      }

      toast.success("Your version has been submitted.");
    } catch {
      toast.error("Something went wrong. Please try again.");
    }
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
            Flip a post
          </h1>
          <p className="text-base leading-7 text-muted-foreground">
            Paste a post and we’ll generate a flipped version.
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
            <div className="space-y-2">
              <Label htmlFor="modelSelect">Model</Label>
              <select
                id="modelSelect"
                value={selectedModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                className="h-10 w-full rounded-md border bg-background px-3 py-2 text-sm"
                disabled={isFlipping || isLoadingModels}
              >
                {modelOptions.length === 0 ? (
                  <option value={FALLBACK_MODEL_ID}>{FALLBACK_MODEL_ID}</option>
                ) : (
                  modelOptions.map((model) => (
                    <option key={model.model_id} value={model.model_id}>
                      {model.display_name}
                    </option>
                  ))
                )}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Examples</Label>
              <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto py-1 whitespace-nowrap">
                {isLoadingExamples ? (
                  <div className="flex-shrink-0 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
                    Loading examples…
                  </div>
                ) : (
                  exampleSuggestions.map((example) => (
                    <Button
                      key={example.id}
                      variant="outline"
                      size="sm"
                      onClick={() => applyExample(example)}
                      disabled={isLoadingRandomExample}
                      className="flex-shrink-0 text-[0.75rem] py-1 px-2"
                    >
                      {example.title}
                    </Button>
                  ))
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={fetchRandomExample}
                  disabled={isLoadingRandomExample || isLoadingExamples}
                  className="flex-shrink-0 text-[0.75rem] py-1 px-2"
                >
                  {isLoadingRandomExample ? "Loading…" : "Get a random example"}
                </Button>
              </div>
            </div>
            <Textarea
              id="inputText"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Paste your post here…"
              className="min-h-36 resize-y"
            />
          </CardContent>
          <CardFooter>
            <Button onClick={handleFlip} disabled={!canFlip || isFlipping}>
              {isFlipping ? "Flipping…" : "Flip"}
            </Button>
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
                    disabled={isSubmittingThumb}
                  >
                    {isSubmittingThumb ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ThumbsUp className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    type="button"
                    variant={feedback === "down" ? "default" : "outline"}
                    size="icon"
                    onClick={handleThumbDown}
                    aria-label="Thumbs down"
                    disabled={isSubmittingThumb}
                  >
                    {isSubmittingThumb ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <ThumbsDown className="h-4 w-4" />
                    )}
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
                <CardFooter>
                  <Button
                    type="button"
                    onClick={handleSubmitCustom}
                    disabled={customVersion.trim().length === 0}
                  >
                    Submit
                  </Button>
                </CardFooter>
              </Card>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
