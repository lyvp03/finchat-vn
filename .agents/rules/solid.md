---
trigger: always_on
---



## Engineering Defaults

- Prefer simple, readable, maintainable code over clever code.
- Optimize for high cohesion and low coupling.
- Keep modules, classes, and functions focused on one clear responsibility.
- Apply SOLID only when it materially improves clarity, testability, or change isolation.
- Do not introduce abstractions just to satisfy design principles in the abstract.
- Preserve coherence across naming, responsibilities, interfaces, and behavior.
- Prefer explicit data flow and clear boundaries over hidden side effects.
- Avoid premature optimization, premature generalization, and speculative extension points.
- Minimize cross-module knowledge and dependencies.
- If a tradeoff adds complexity, explain why that complexity is justified.

## Change Guidance

- Make the smallest change that solves the problem correctly end-to-end.
- Refactor when it directly improves the target change, removes duplication, or reduces clear maintenance risk.
- Extract helpers when it improves comprehension, not only to reduce line count.
- Keep code easy to scan and reason about in one pass.
- Add or update tests when behavior changes or implementation risk is non-trivial.
- Leave touched code in a more coherent state than you found it.
