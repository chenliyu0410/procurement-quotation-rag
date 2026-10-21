import { afterEach, expect, it, vi } from "vitest";
import { queryProcurement } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("sends the last two conversation turns with a follow-up query", async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ answer: "ok" }) });
  vi.stubGlobal("fetch", fetcher);
  const history = [{ role: "user", content: "找資訊服務" }, { role: "assistant", content: "有案件" }];
  await queryProcurement("那其中最低呢", history);
  expect(JSON.parse(fetcher.mock.calls[0][1].body).history).toEqual(history);
});
