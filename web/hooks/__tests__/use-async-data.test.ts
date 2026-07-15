import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAsyncData } from "../use-async-data";

describe("useAsyncData", () => {
  it("loads data on mount and flips loading to false", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 42 });
    const { result } = renderHook(() => useAsyncData(fetcher, []));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("captures the error message on failure", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useAsyncData(fetcher, []));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("boom");
  });

  it("does not fetch when enabled is false", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });
    const { result } = renderHook(() => useAsyncData(fetcher, [], { enabled: false }));

    expect(result.current.loading).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
    expect(result.current.data).toBeNull();
  });

  it("reload(true) refreshes data without flipping loading", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ value: 1 }).mockResolvedValueOnce({ value: 2 });
    const { result } = renderHook(() => useAsyncData(fetcher, []));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.reload(true);
    });

    expect(result.current.data).toEqual({ value: 2 });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("re-fetches when a dependency changes", async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: true });
    const { rerender } = renderHook(({ dep }) => useAsyncData(fetcher, [dep]), {
      initialProps: { dep: 1 },
    });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));

    rerender({ dep: 2 });
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  });

  it("ignores a stale response that resolves after a newer request", async () => {
    // Regression test: an older in-flight request (for the previous dep
    // value) must not clobber state if it resolves after a newer request
    // (for the current dep value) has already resolved.
    const resolvers: Record<number, (value: { dep: number }) => void> = {};
    const fetcher = vi.fn(
      (dep: number) =>
        new Promise<{ dep: number }>((resolve) => {
          resolvers[dep] = resolve;
        }),
    );

    const { result, rerender } = renderHook(({ dep }) => useAsyncData(() => fetcher(dep), [dep]), {
      initialProps: { dep: 1 },
    });
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith(1));

    rerender({ dep: 2 });
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith(2));

    // Resolve the newer request first, then the stale older one.
    await act(async () => {
      resolvers[2]({ dep: 2 });
    });
    await act(async () => {
      resolvers[1]({ dep: 1 });
    });

    expect(result.current.data).toEqual({ dep: 2 });
    expect(result.current.loading).toBe(false);
  });

  it("keeps a previous error visible until a silent reload's outcome is known", async () => {
    // Regression test: reload(true) used to call setError(null) up front,
    // clearing a previously shown error immediately — even before the new
    // fetch had resolved. A poller displaying `error` in a banner would see
    // it flash blank on every tick regardless of whether the retry succeeded.
    const fetcher = vi.fn().mockRejectedValueOnce(new Error("first failure"));
    const { result } = renderHook(() => useAsyncData(fetcher, []));
    await waitFor(() => expect(result.current.error).toBe("first failure"));

    let resolveSecond!: (value: { ok: true }) => void;
    fetcher.mockImplementationOnce(() => new Promise((resolve) => { resolveSecond = resolve; }));

    let reloadPromise!: Promise<void>;
    act(() => {
      reloadPromise = result.current.reload(true);
    });

    // The second fetch hasn't resolved yet — the old error must still show.
    expect(result.current.error).toBe("first failure");

    await act(async () => {
      resolveSecond({ ok: true });
      await reloadPromise;
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data).toEqual({ ok: true });
  });
});
