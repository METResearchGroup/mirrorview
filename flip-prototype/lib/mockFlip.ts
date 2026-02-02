export function mockFlip(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) return "";

  // Deterministic mock “flip” for the prototype:
  // - Reverse the word order (keeps punctuation attached to words).
  // - Prefix a short label so it's obvious this is mocked.
  const flipped = trimmed.split(/\s+/).reverse().join(" ");
  return `Flipped (mock): ${flipped}`;
}

