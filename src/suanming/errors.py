from __future__ import annotations

from typing import Any


class SuanmingError(Exception):
    code = "suanming_error"

    def __init__(
        self,
        message: str,
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


class UnknownPipelineError(SuanmingError):
    code = "unknown_pipeline"


class InputValidationError(SuanmingError):
    code = "input_validation_error"


class InputDecodeError(SuanmingError):
    code = "input_decode_error"


class AssetManifestError(SuanmingError):
    code = "asset_manifest_error"
