# Google Gemini SDK Migration Research (2025)

**Status:** Research Complete
**Date:** 2025-12-29
**Target Version:** Google Gen AI SDK v1.0+ (`google-genai`)
**Legacy Version:** `google-generativeai` (Deprecated Dec 2025)

## Executive Summary

The Python SDK for Google Gemini has undergone a complete rewrite. The previous package `google-generativeai` is now **deprecated** and archived. The new official SDK is `google-genai`. This is a major breaking change requiring a full migration of imports, client initialization, and method calls. The new SDK unifies the Gemini Developer API and Vertex AI into a single interface.

## 1. Package Installation

| Old (Deprecated) | New (Required) |
|------------------|----------------|
| `pip install google-generativeai` | `pip install google-genai` |

## 2. Import Changes

**Old Pattern:**
```python
import google.generativeai as genai
from google.generativeai import generation_types
```

**New Pattern:**
```python
from google import genai
from google.genai import types
from pydantic import BaseModel # Recommended for schemas
```

## 3. Client Initialization

The new SDK introduces a unified `Client` class. It no longer relies on module-level `configure` calls.

**Old Pattern:**
```python
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
```

**New Pattern (Sync):**
```python
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
# No separate "model" object instantiation required for calls
```

**New Pattern (Async) - CRITICAL CHANGE:**
The async client is now accessed via the `.aio` property of the sync client, or context manager.
```python
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
async_client = client.aio

# OR Context Manager
async with genai.Client(api_key=...).aio as client:
    ...
```

## 4. Content Generation

The method signatures have changed significantly. The `model` is now a parameter in the method call, not the object itself.

**Old Pattern (Async):**
```python
response = await model.generate_content_async(
    prompt,
    generation_config=config
)
print(response.text)
```

**New Pattern (Async):**
```python
response = await client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.7
    )
)
print(response.text)
```

## 5. Structured Output (JSON)

The new SDK natively integrates with Pydantic for schema definition, replacing the manual dictionary-based schemas.

**Old Pattern:**
```python
schema = {
    "type": "OBJECT",
    "properties": {
        "recipe_name": {"type": "STRING"},
    }
}
config = genai.GenerationConfig(
    response_mime_type="application/json",
    response_schema=schema
)
```

**New Pattern:**
```python
from pydantic import BaseModel

class Recipe(BaseModel):
    recipe_name: str

response = await client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents="Cookie recipe",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=Recipe
    )
)
# Automatic parsing available in some contexts, but raw JSON text is standard
```

## 6. Error Handling

Exceptions have moved.

**Old Pattern:**
```python
from google.api_core import exceptions
except exceptions.ResourceExhausted:
```

**New Pattern:**
The new SDK still wraps some `google.api_core` exceptions but exposes them more cleaner.
*Verification Pending*: Standard `google.api_core.exceptions` may still be caught, but check `from google.genai import errors` (if available) or standard exceptions. The documentation primarily shows standard usage.

## 7. Migration Checklist for FBScrapeIdeas

1.  **Update `requirements.txt`**: Replace `google-generativeai` with `google-genai`.
2.  **Refactor `ai/gemini_provider.py`**:
    *   Change imports.
    *   Update `GeminiProvider.__init__` to instantiate `genai.Client`.
    *   Update `generate_content` methods to use `client.aio.models.generate_content`.
    *   Pass `model` string (e.g., `gemini-2.0-flash`) during the call, not initialization.
3.  **Update Schemas**:
    *   If using `gemini_schema.json`, load it and pass it to `types.GenerateContentConfig`.
    *   Alternatively, convert strictly defined schemas to Pydantic models for better validation.

## 8. Reference Documentation
*   **Migration Guide**: https://ai.google.dev/gemini-api/docs/migrate
*   **PyPI**: https://pypi.org/project/google-genai/
*   **GitHub**: https://github.com/googleapis/python-genai
