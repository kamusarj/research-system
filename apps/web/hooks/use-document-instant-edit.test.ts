import { expect, it } from "vitest";
import { ApiError } from "@/lib/api";
import { instantEditFailure } from "./use-document-instant-edit";

it("classifies transient proxy and provider failures as retryable", () => {
  expect(instantEditFailure(new ApiError("proxy failed", "request_error", 500))).toEqual({
    key: "instantEditTemporaryFailure",
    retryable: true,
  });
  expect(instantEditFailure(new ApiError("invalid", "AI_RESPONSE_INVALID", 502))).toEqual({
    key: "instantEditInvalidResponse",
    retryable: true,
  });
});

it("keeps no-change and configuration failures non-retryable", () => {
  expect(instantEditFailure(new ApiError("same", "AI_EDIT_NO_CHANGE", 409))).toEqual({
    key: "instantEditNoChange",
    retryable: false,
  });
  expect(instantEditFailure(new ApiError("auth", "AI_PROVIDER_AUTH_FAILED", 503))).toEqual({
    key: "instantEditProviderAuthFailed",
    retryable: false,
  });
});
