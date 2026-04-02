---
name: react-best-practices
description: "Optimize React and Next.js performance by eliminating request waterfalls with Promise.all, reducing bundle size via direct imports over barrel files, implementing code splitting with next/dynamic, memoizing components with React.memo/useMemo, configuring ISR/SSG for caching, and optimizing images with next/image. Triggers on slow page loads, large bundle size, excessive re-renders, rendering bottlenecks, or Core Web Vitals regressions in React/Next.js apps."
---

# React Best Practices

Performance optimization patterns for React and Next.js, prioritized by impact. 40+ rules across 8 categories from Vercel Engineering.

| Priority | Category | Impact |
|----------|----------|--------|
| 1 | Eliminating Waterfalls | CRITICAL |
| 2 | Bundle Size Optimization | CRITICAL |
| 3 | Server-Side Performance | HIGH |
| 4 | Client-Side Data Fetching | MEDIUM-HIGH |
| 5 | Re-render Optimization | MEDIUM |
| 6 | Rendering Performance | MEDIUM |
| 7 | JavaScript Performance | LOW-MEDIUM |
| 8 | Advanced Patterns | LOW |

## Critical Patterns (Apply First)

### Eliminate Waterfalls

Sequential awaits are the #1 performance killer. Parallelize independent async work:

```tsx
// BAD: sequential waterfall — each await blocks the next
const user = await getUser(id);
const posts = await getPosts(id);
const analytics = await getAnalytics(id);

// GOOD: parallel fetching with Promise.all
const [user, posts, analytics] = await Promise.all([
  getUser(id),
  getPosts(id),
  getAnalytics(id),
]);
```

Also: defer `await` into branches, start promises early and await late, use Suspense boundaries to stream content progressively.

### Reduce Bundle Size

Barrel file re-exports pull in entire modules. Import directly from source:

```tsx
// BAD: barrel import pulls in every export from the package
import { Button } from '@/components';

// GOOD: direct import — only Button code is bundled
import { Button } from '@/components/Button';
```

Use `next/dynamic` for heavy components not needed on initial render:

```tsx
import dynamic from 'next/dynamic';

const HeavyChart = dynamic(() => import('@/components/Chart'), {
  loading: () => <ChartSkeleton />,
});
```

Also: defer non-critical third-party libraries, preload based on user intent.

## High-Impact Server Patterns

- Use `React.cache()` for per-request deduplication
- Use LRU cache for cross-request caching
- Minimize serialization at RSC boundaries
- Parallelize data fetching with component composition

## Medium-Impact Client Patterns

- Use SWR for automatic request deduplication
- Defer state reads to usage point
- Use lazy state initialization for expensive values
- Use derived state subscriptions
- Apply `startTransition` for non-urgent updates

## Rendering Patterns

- Animate SVG wrappers, not SVG elements directly
- Use `content-visibility: auto` for long lists
- Prevent hydration mismatch with inline scripts
- Use explicit conditional rendering (`? :` not `&&`)

## JavaScript Patterns

- Batch DOM CSS changes via classes
- Build index maps for repeated lookups
- Cache repeated function calls
- Use `toSorted()` instead of `sort()` for immutability
- Early length check for array comparisons

## Verification Workflow

After applying optimizations, verify the impact:

1. **Bundle size** — Run `npx @next/bundle-analyzer` or `npx webpack-bundle-analyzer` to confirm reduced chunk sizes and eliminated barrel file bloat.
2. **Load performance** — Run Lighthouse (`npx lighthouse <url> --view`) targeting LCP < 2.5s, FID < 100ms, CLS < 0.1.
3. **Re-render profiling** — Use React DevTools Profiler to confirm components are not re-rendering unnecessarily. Look for flamegraph bars that should not appear on a given interaction.
4. **Waterfall check** — Open DevTools Network tab, sort by waterfall column, and confirm parallel requests replaced sequential chains.

## References

Full documentation with code examples:

- `references/react-performance-guidelines.md` — Complete guide with all patterns
- `references/rules/` — Individual rule files organized by category

Look up specific patterns:
```
grep -l "suspense" references/rules/
grep -l "barrel" references/rules/
grep -l "swr" references/rules/
```

### Rule categories in `references/rules/`

- `async-*` — Waterfall elimination patterns
- `bundle-*` — Bundle size optimization
- `server-*` — Server-side performance
- `client-*` — Client-side data fetching
- `rerender-*` — Re-render optimization
- `rendering-*` — DOM rendering performance
- `js-*` — JavaScript micro-optimizations
- `advanced-*` — Advanced patterns
