"use client";

import { useState, useEffect, useRef } from "react";

interface TypingRendererProps {
  content: string;
  /** Characters per tick to reveal */
  charsPerTick?: number;
  /** Milliseconds between ticks */
  intervalMs?: number;
  /** Called when typing finishes */
  onComplete?: () => void;
  /** Render function for the revealed text so far */
  children: (revealedText: string, isDone: boolean) => React.ReactNode;
}

/**
 * Progressive text reveal that preserves markdown structure.
 *
 * Reveals character-by-character but snaps to complete markdown lines:
 * when the cursor reaches a newline followed by a markdown token
 * (-, *, #, digit.), it includes the entire next line to avoid
 * breaking markdown parsing mid-token.
 */
export function TypingRenderer({
  content,
  charsPerTick = 8,
  intervalMs = 20,
  onComplete,
  children,
}: TypingRendererProps) {
  const [charIndex, setCharIndex] = useState(0);
  const contentRef = useRef(content);
  const completedRef = useRef(false);

  // Reset on content change
  useEffect(() => {
    if (contentRef.current !== content) {
      contentRef.current = content;
      completedRef.current = false;
      setCharIndex(0);
    }
  }, [content]);

  useEffect(() => {
    if (charIndex >= content.length) {
      if (!completedRef.current) {
        completedRef.current = true;
        onComplete?.();
      }
      return;
    }

    const timer = setTimeout(() => {
      let nextIndex = Math.min(charIndex + charsPerTick, content.length);

      // Snap forward to the end of the current line to avoid
      // cutting markdown tokens (bullets, headings, bold) mid-parse
      const nextNewline = content.indexOf("\n", nextIndex);
      if (nextNewline !== -1 && nextNewline - nextIndex < 40) {
        // If we're close to a newline, snap to it
        nextIndex = nextNewline + 1;
      }

      setCharIndex(nextIndex);
    }, intervalMs);

    return () => clearTimeout(timer);
  }, [charIndex, content, charsPerTick, intervalMs, onComplete]);

  // Snap revealed text to the last complete line to keep markdown valid
  let revealedEnd = charIndex;
  if (revealedEnd < content.length) {
    // Find the last newline before revealedEnd
    const lastNewline = content.lastIndexOf("\n", revealedEnd);
    // Only snap back if the remaining partial line starts with a markdown token
    if (lastNewline > 0) {
      const partialLine = content.slice(lastNewline + 1, revealedEnd);
      const restOfLine = content.slice(revealedEnd, content.indexOf("\n", revealedEnd));
      // If the partial line is very short and looks like a broken markdown token, snap to lastNewline
      if (partialLine.length < 5 && /^[-*#\d]/.test(partialLine) && restOfLine.length > 0) {
        revealedEnd = lastNewline;
      }
    }
  }

  const revealedText = content.slice(0, revealedEnd);
  const isDone = charIndex >= content.length;

  return <>{children(revealedText, isDone)}</>;
}

/**
 * Blinking cursor indicator shown at the end of streaming text.
 */
export function StreamCursor() {
  return (
    <span className="inline-block w-[2px] h-[1.1em] bg-primary animate-pulse ml-0.5 align-text-bottom" />
  );
}
