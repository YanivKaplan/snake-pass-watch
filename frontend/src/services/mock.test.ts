import { beforeEach, describe, expect, it } from "vitest";
import { createMockService } from "./mock";

beforeEach(() => {
  window.localStorage.clear();
});

describe("mock backend", () => {
  it("signs up and logs in users", async () => {
    const svc = createMockService();
    const u = await svc.signup("alice", "pass1234");
    expect(u.username).toBe("alice");
    expect(await svc.currentUser()).toEqual(u);
    await svc.logout();
    expect(await svc.currentUser()).toBeNull();
    const back = await svc.login("alice", "pass1234");
    expect(back.id).toBe(u.id);
  });

  it("rejects duplicate usernames", async () => {
    const svc = createMockService();
    await svc.signup("bob", "pass1234");
    await expect(svc.signup("bob", "other1234")).rejects.toThrow();
  });

  it("computes leaderboard with best score per user per mode", async () => {
    const svc = createMockService();
    await svc.signup("alice", "pass1234");
    await svc.submitScore("walls", 5);
    await svc.submitScore("walls", 10);
    await svc.submitScore("wrap", 3);
    await svc.logout();
    await svc.signup("bob", "pass1234");
    await svc.submitScore("walls", 7);

    const wallsTop = await svc.getLeaderboard("walls");
    expect(wallsTop.map((s) => [s.username, s.score])).toEqual([
      ["alice", 10],
      ["bob", 7],
    ]);
    const wrapTop = await svc.getLeaderboard("wrap");
    expect(wrapTop).toHaveLength(1);
    expect(wrapTop[0].score).toBe(3);
  });

  it("tracks active games and notifies subscribers", async () => {
    const svc = createMockService();
    await svc.signup("alice", "pass1234");
    let calls: number[] = [];
    const unsub = svc.subscribeToActiveGames((g) => calls.push(g.length));
    await svc.publishGameState(
      {
        width: 10,
        height: 10,
        snake: [[1, 1]],
        food: [2, 2],
        dir: "right",
        alive: true,
      },
      "walls",
      0,
    );
    expect(calls.at(-1)).toBe(1);
    await svc.endGame();
    expect(calls.at(-1)).toBe(0);
    unsub();
  });
});
