{
  "providers": {
    "litellm": {
      "baseUrl": "https://llm.grehg2.xyz/v1",
      "api": "openai-completions",
      "apiKey": "{{ op://Infra/LiteLLM/master_key }}",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "local-small",
          "name": "local-small: Qwen 3.6 35B A3B, thinking off (moria, else dungeon)",
          "contextWindow": 65536,
          "maxTokens": 32768,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "local-lab",
          "name": "local-lab: the same model, dungeon only",
          "contextWindow": 65536,
          "maxTokens": 32768,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "local-big",
          "name": "local-big: Qwen 3.8 27B, moria only (fails when away)",
          "contextWindow": 65536,
          "maxTokens": 32768,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "cloud",
          "name": "cloud: DeepSeek Flash via the gateway (metered)",
          "reasoning": true,
          "thinkingLevelMap": {
            "minimal": null,
            "low": "low",
            "medium": null,
            "high": "high",
            "max": "max"
          },
          "contextWindow": 1000000,
          "maxTokens": 384000,
          "input": ["text", "image"],
          "cost": { "input": 0.3, "output": 1.2, "cacheRead": 0.006, "cacheWrite": 0 },
          "compat": {
            "supportsStore": false,
            "supportsDeveloperRole": false,
            "maxTokensField": "max_tokens",
            "requiresReasoningContentOnAssistantMessages": true,
            "thinkingFormat": "deepseek",
            "supportsStrictMode": true,
            "supportsReasoningEffort": true
          },
          "inputLimits": {
            "images": {
              "resize": { "maxWidth": 2000, "maxHeight": 2000, "maxBytes": 4718592, "jpegQuality": 80 }
            }
          }
        }
      ]
    },
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
          "id": "Qwen3.6-35B-A3B-4bit",
          "name": "Qwen 3.6 35B A3B 4-bit (MoE, 131 t/s, coding DEFAULT)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Qwen3.6-35B-A3B-4bit:lab",
          "name": "Qwen 3.6 35B A3B 4-bit, thinking off (dungeon's one model)",
          "contextWindow": 65536,
          "maxTokens": 32768,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Qwen3.6-35B-A3B-4bit-DWQ",
          "name": "Qwen 3.6 35B A3B 4-bit DWQ (MoE, 104 t/s, quality-leaning)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Qwen3.6-35B-A3B-8bit",
          "name": "Qwen 3.6 35B A3B 8-bit (thinking, 262k ctx, 81k max, heavy)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Swift-1.5-Qwen3.8-27b-oQ4e-mtp",
          "name": "Swift 1.5 Qwen 3.8 27B oQ4e + MTP (dense, ~37 t/s, hard-coding specialist)",
          "contextWindow": 262144,
          "maxTokens": 81920,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "Qwen3.5-9B-MLX-4bit",
          "name": "Qwen 3.5 9B 4-bit (dense, small)",
          "contextWindow": 131072,
          "maxTokens": 32768,
          "input": ["text"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        },
        {
          "id": "gemma-4-26b-a4b-it-qat-4bit",
          "name": "Gemma 4 26B A4B QAT (summarization, 256k ctx, fast)",
          "contextWindow": 262144,
          "maxTokens": 32768,
          "input": ["text", "image"],
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        }
      ]
    }
  }
}
