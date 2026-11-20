import { describe, expect, it } from "vitest";
import { emptyCV } from "../types/cv";
import { navItemsFor } from "./SectionNav";

describe("navItemsFor", () => {
  it("lists every section once, with a label, for both profiles", () => {
    for (const profile of ["experienced", "fresher"] as const) {
      const items = navItemsFor({ ...emptyCV(), profile });
      const ids = items.map((i) => i.id);
      expect(new Set(ids).size).toBe(ids.length);
      expect(items.every((i) => i.label.length > 0)).toBe(true);
    }
  });
});
