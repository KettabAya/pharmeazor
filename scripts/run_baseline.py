import json
from pathlib import Path
from pharmeazor.answer.llm_client import ask_llm, get_call_count

PROMPT = "Quelle est la DCI de DOLIPRANE ?"

answers = {}

for i in range(3):
    print(f"\n===== RUN {i+1} =====")
    answers[f"run_{i+1}"] = ask_llm(PROMPT + "\n" * (i + 1), use_cache=False)
    print(answers[f"run_{i+1}"])

out = Path("eval/llm_alone_test.json")
out.parent.mkdir(exist_ok=True)

out.write_text(json.dumps(
    {
        "prompt": PROMPT,
        "answers": answers,
        "api_calls_used": get_call_count()
    },
    indent=2,
    ensure_ascii=False
))

print(f"\nSaved answers to {out}")
print(f"Total API calls: {get_call_count()}")