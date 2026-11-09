export type DiffPart =
  | { kind: "text"; text: string }
  | { kind: "del"; text: string }
  | { kind: "add"; text: string };

function tokens(value: string): string[] {
  return value.match(/\S+\s*/g) ?? [];
}

/** Longest common subsequence opcodes over word tokens. */
function opcodes(a: string[], b: string[]): Array<["equal" | "change", number, number, number, number]> {
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const ops: Array<["equal" | "change", number, number, number, number]> = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      const i0 = i;
      const j0 = j;
      while (i < n && j < m && a[i] === b[j]) {
        i += 1;
        j += 1;
      }
      ops.push(["equal", i0, i, j0, j]);
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      const i0 = i;
      while (i < n && (j >= m || a[i] !== b[j]) && dp[i + 1][j] >= dp[i][j + 1]) i += 1;
      if (i === i0) i += 1;
      ops.push(["change", i0, i, j, j]);
    } else {
      const j0 = j;
      while (j < m && (i >= n || a[i] !== b[j]) && dp[i][j + 1] > dp[i + 1][j]) j += 1;
      if (j === j0) j += 1;
      ops.push(["change", i, i, j0, j]);
    }
  }
  if (i < n || j < m) ops.push(["change", i, n, j, m]);
  return ops;
}

function splitTrail(value: string): { word: string; trail: string } {
  const word = value.trimEnd();
  return { word, trail: value.slice(word.length) };
}

/** Word diff. A replacement keeps one trailing space, after the added word. */
export function wordDiff(oldText: string, newText: string): DiffPart[] {
  const a = tokens(oldText);
  const b = tokens(newText);
  const parts: DiffPart[] = [];
  for (const [kind, i1, i2, j1, j2] of opcodes(a, b)) {
    if (kind === "equal") {
      parts.push({ kind: "text", text: a.slice(i1, i2).join("") });
      continue;
    }
    const oldChunk = a.slice(i1, i2).join("");
    const newChunk = b.slice(j1, j2).join("");
    const oldSplit = splitTrail(oldChunk);
    const newSplit = splitTrail(newChunk);
    if (oldSplit.word && newSplit.word) {
      parts.push({ kind: "del", text: oldSplit.word });
      parts.push({ kind: "add", text: newSplit.word });
      if (newSplit.trail) parts.push({ kind: "text", text: newSplit.trail });
    } else if (oldSplit.word) {
      parts.push({ kind: "del", text: oldSplit.word });
      if (oldSplit.trail) parts.push({ kind: "text", text: oldSplit.trail });
    } else if (newSplit.word) {
      parts.push({ kind: "add", text: newSplit.word });
      if (newSplit.trail) parts.push({ kind: "text", text: newSplit.trail });
    }
  }
  return parts;
}

/** New text only, with added words marked. No strikethrough. */
export function addedOnly(oldText: string, newText: string): DiffPart[] {
  return wordDiff(oldText, newText).filter((part) => part.kind !== "del");
}
