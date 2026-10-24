import { expect, it } from "vitest";

import packageJson from "../package.json";

it("keeps typecheck read-only across host and container users", () => {
  expect(packageJson.scripts.typecheck).toContain("--incremental false");
});
