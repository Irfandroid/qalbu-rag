---
name: typescript-strict
description: Strict TypeScript, precise interfaces, and runtime schema validation with Zod. Use when writing or reviewing TypeScript, typing API boundaries, eliminating any, modeling state with unions, validating env or request payloads, or when Python code needs equivalent strict typing with mypy and Pydantic.
---

# TypeScript Strict — Make Illegal States Unrepresentable

The compiler is the cheapest test you will ever run. Push validation to the
boundary once, then let types flow inward without re-checking.

## Required tsconfig

```jsonc
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "useUnknownInCatchVariables": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "moduleResolution": "bundler",
    "target": "ES2022"
  }
}
```

Do not weaken flags per-file to get a build green. Fix the type or validate the
unknown.

## No `any`

- `any` disables checking for everything it touches. Use `unknown` at boundaries.
- Narrow `unknown` with a type guard, a Zod schema, or an `in`/`typeof` check.
- Type assertions (`as`) are allowed only in tests or after a runtime check that
  the compiler cannot see. Add a comment explaining why.
- Avoid `!` non-null assertions. Handle the null case or throw with context.
- `@ts-expect-error` needs a reason and must be removed when upstream is fixed.

```ts
function isUser(value: unknown): value is User {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "string"
  );
}
```

## Model with unions, not optional soup

```ts
// Bad: impossible combinations are representable
type Request = {
  status?: "idle" | "loading" | "success" | "error";
  data?: User;
  error?: string;
};

// Good: each state carries exactly what it needs
type Request =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: User }
  | { status: "error"; error: string };
```

```ts
function assertNever(value: never): never {
  throw new Error(`Unhandled case: ${JSON.stringify(value)}`);
}

switch (state.status) {
  case "idle": return null;
  case "loading": return <Spinner />;
  case "success": return <Profile user={state.data} />;
  case "error": return <ErrorNote message={state.error} />;
  default: return assertNever(state);
}
```

## Precise interfaces

- Prefer `type` for unions and composition; `interface` for extendable objects.
- Mark properties `readonly` when they must not be mutated.
- Use `satisfies` to check a value without widening it.
- Use `as const` for literal tables; derive unions from them.
- Use branded types for IDs and units (`UserId`, `Cents`) when mixing is a real risk.
- Avoid enums; use `as const` objects or string unions.
- Do not export types from implementation files just to satisfy tests; export the contract.

```ts
export const ROLES = ["admin", "editor", "viewer"] as const;
export type Role = (typeof ROLES)[number];

const config = {
  retries: 3,
  mode: "strict",
} satisfies AppConfig;
```

## Zod at every boundary

Parse, do not merely validate. The parsed value is the source of truth; derive
the static type from the schema.

```ts
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  role: z.enum(["admin", "editor", "viewer"]),
  createdAt: z.coerce.date(),
});

export type User = z.infer<typeof UserSchema>;

export function parseUser(input: unknown): User {
  const result = UserSchema.safeParse(input);
  if (!result.success) {
    throw new ValidationError(result.error.flatten());
  }
  return result.data;
}
```

Rules:
- Validate at the edges: HTTP body/query, env vars, `localStorage`, SSE/WS messages, third-party responses.
- One schema per boundary; do not duplicate the shape by hand.
- Use `.strict()` on external objects when unknown keys signal a contract drift.
- Use `z.discriminatedUnion` for tagged payloads.
- Use `z.input` for form values and `z.output` for parsed data.
- Never trust `JSON.parse` output; it is `any`/`unknown`.
- Format Zod errors into field-level messages for the UI.

```ts
const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  PORT: z.coerce.number().int().positive().default(3000),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});
export const env = EnvSchema.parse(process.env);
```

## Generics and utility types

- Constrain generics: `<T extends { id: string }>`, not `<T>`.
- Avoid generic parameters used once; they add noise.
- Prefer `Pick`, `Omit`, `Partial` over re-declaring shapes.
- Do not use `Partial<T>` for domain state; it hides required invariants.
- `Record<string, T>` implies every key exists. With `noUncheckedIndexedAccess`, reads are `T | undefined` — handle it.

## Python counterpart (this repo)

- `mypy` with `disallow_untyped_defs`, `no_implicit_optional`, `warn_unused_ignores`.
- Pydantic v2 models at API, config, and provider boundaries; `model_validate` before use.
- Annotate public functions and returns. `Any` only at a validated boundary.
- Use `Literal`, `Protocol`, and `TypedDict` instead of loose dicts.
- Keep `pyproject.toml` mypy settings authoritative.

## Review checklist

- [ ] `strict` and the extra flags are on.
- [ ] No new `any`, `as`, or `!` without justification.
- [ ] External data is parsed by a schema at the edge.
- [ ] Types are derived from schemas, not duplicated.
- [ ] Unions cover all states; switches are exhaustive.
- [ ] Optional fields are genuinely optional, not lazily added.
- [ ] Env vars validated at startup.
