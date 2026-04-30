{
  "providers": {
    "omlx": {
      "baseUrl": "http://localhost:8000/v1",
      "api": "openai-completions",
      "apiKey": "{{ op://Infra/oMLX/api_key }}",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "Qwen3.6-35B-A3B-8bit",
          "name": "Qwen 3.6 35B A3B (thinking, 262k ctx, 81k max, heavy)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Qwen3.6-27B-8bit",
          "name": "Qwen 3.6 27B 8-bit (thinking, 262k ctx, balanced)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Qwen3.6-27B-4bit",
          "name": "Qwen 3.6 27B 4-bit (thinking, 262k ctx, fast)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "gemma-4-26b-a4b-it-4bit",
          "name": "Gemma 4 26B A4B (summarization, 256k ctx, fast)",
          "contextWindow": 262144,
          "maxTokens": 32768,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "gpt-oss-120b-heretic-v2-mxfp4-q8-hi-mlx",
          "name": "GPT-OSS 120B Heretic v2 (local)",
          "contextWindow": 32768,
          "maxTokens": 32768,
          "input": ["text"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        }
      ]
    }
  }
}
