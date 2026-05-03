"use client";

import ReactMarkdown from "react-markdown";
import { ComponentPropsWithoutRef } from "react";

/**
 * Highlight financial numbers inline:
 * - +X% or +X.X% → green
 * - -X% or -X.X% → red
 * - Prices (xxx,xxx,xxx) → bold
 */
function highlightFinancialText(text: string): React.ReactNode[] {
  // Pattern: signed percentages, VND amounts, USD amounts
  const pattern = /([+-]\d+[\d,.]*\s*%)|(\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:\s*(?:triệu|tr|đồng|đ|VND|USD))?)|((?:\$|USD\s*)\d+[\d,.]*)/g;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const value = match[0];
    const isPositive = value.startsWith("+");
    const isNegative = value.startsWith("-");

    if (isPositive || isNegative) {
      parts.push(
        <span
          key={match.index}
          className={`font-semibold tabular-nums ${isPositive ? "text-emerald-500" : "text-red-500"}`}
        >
          {value}
        </span>
      );
    } else {
      // Neutral number — just bold
      parts.push(
        <span key={match.index} className="font-semibold tabular-nums">
          {value}
        </span>
      );
    }

    lastIndex = match.index + value.length;
  }

  // Remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

/**
 * Custom paragraph renderer that highlights financial numbers.
 */
function FinancialParagraph(props: ComponentPropsWithoutRef<"p">) {
  const { children, ...rest } = props;

  const processChildren = (child: React.ReactNode): React.ReactNode => {
    if (typeof child === "string") {
      return <>{highlightFinancialText(child)}</>;
    }
    return child;
  };

  return (
    <p {...rest}>
      {Array.isArray(children)
        ? children.map((child, i) => <span key={i}>{processChildren(child)}</span>)
        : processChildren(children)}
    </p>
  );
}

/**
 * Custom list item renderer with financial highlighting.
 */
function FinancialListItem(props: ComponentPropsWithoutRef<"li">) {
  const { children, ...rest } = props;

  const processChildren = (child: React.ReactNode): React.ReactNode => {
    if (typeof child === "string") {
      return <>{highlightFinancialText(child)}</>;
    }
    return child;
  };

  return (
    <li {...rest}>
      {Array.isArray(children)
        ? children.map((child, i) => <span key={i}>{processChildren(child)}</span>)
        : processChildren(children)}
    </li>
  );
}

interface FinancialMarkdownProps {
  content: string;
}

/**
 * Custom unordered list with explicit bullet styles.
 */
function FinancialUl(props: ComponentPropsWithoutRef<"ul">) {
  return <ul className="list-disc pl-5 my-2 space-y-1" {...props} />;
}

/**
 * Custom ordered list with explicit number styles.
 */
function FinancialOl(props: ComponentPropsWithoutRef<"ol">) {
  return <ol className="list-decimal pl-5 my-2 space-y-1" {...props} />;
}

/**
 * ReactMarkdown wrapper with custom renderers for financial data:
 * - Positive % → green
 * - Negative % → red
 * - Large numbers → bold tabular
 * - Bullet lists → explicit disc markers
 */
export function FinancialMarkdown({ content }: FinancialMarkdownProps) {
  return (
    <div className="max-w-none text-[15px] leading-relaxed [&>p]:my-1.5 [&>p]:leading-relaxed">
      <ReactMarkdown
        components={{
          p: FinancialParagraph,
          li: FinancialListItem,
          ul: FinancialUl,
          ol: FinancialOl,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
