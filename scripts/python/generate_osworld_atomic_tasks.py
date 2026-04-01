import argparse
import json
import os
from pathlib import Path

import dashscope


SYSTEM_PROMPT = """You are helping convert a complex desktop task into OSWorld-style atomic tasks.

Your job:
1. Read one original task question.
2. Split it into a small list of atomic OSWorld-style task questions.
3. Each atomic task must have one primary goal, be independently understandable, and sound like an OSWorld instruction.

Requirements:
- Output only JSON.
- Return an object with one key: "atomic_tasks".
- "atomic_tasks" must be a list of strings.
- Each string must be a natural-language OSWorld-style question.
- Keep each atomic task concise and action-oriented.
- Do not include explanations.
- Do not include numbering.
- Do not include subtasks.
- Prefer 4 to 8 atomic tasks.
- Separate Excel-only, Word-only, PowerPoint-only, Outlook-only, and cross-app actions when reasonable.
- Exporting or saving into a final format like PDF/CSV should usually be its own atomic task.
- Do not invent names, worksheet names, file names, paths, numbers, or requirements that are not explicitly present in the original task.
- Prefer stage-level atomic tasks, not click-level, cell-level, or overly fine-grained procedural subtasks.
- Merge simple setup actions into a larger atomic task when they belong to the same evaluation target.
- Keep explicitly required application stages separate when they form different outcomes, such as:
  - Excel data preparation
  - Excel calculation/formatting/chart creation
  - Word report setup/layout/title creation
  - cross-application copy/paste
  - final export
- Do not omit explicitly required stages from the original task.
- If the original task explicitly requires creating or preparing a document in Word, PowerPoint, or another application, preserve that document-creation/setup stage as its own atomic task when it is a meaningful intermediate outcome.
- Prefer goal-oriented wording such as "create a sales table", "prepare a report document", or "create a chart" instead of low-level wording like exact columns, cells, or click sequences, unless those low-level details are essential to the task identity.
- Avoid over-specifying spreadsheet coordinates when the real evaluation target is a higher-level artifact or transformation.
"""


def build_user_prompt(question: str) -> str:
    return f"""Original task question:
{question}

Please convert this into OSWorld-style atomic task questions.
Return JSON only in the form:
{{
  "atomic_tasks": [
    "Could you ...?",
    "Could you ...?"
  ]
}}

Additional guidance:
- Do not invent extra worksheet or document names unless the original task explicitly gives them.
- Do not split basic data entry into multiple tiny tasks unless necessary.
- Keep the result aligned with how OSWorld tasks are usually written: short, clear, single-goal instructions.
- Preserve explicit report/document creation stages as standalone tasks when they are clearly required by the original task.
- Prefer artifact-level descriptions over coordinate-level descriptions.
"""


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OSWorld-style atomic tasks from cleaned questions.json."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(r"C:\OSWorld\Microsoft\questions_clean.json"),
        help="Path to cleaned questions JSON file",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Question index to process when running in single mode",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of consecutive questions to process starting from --index",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("TASK_SPLIT_MODEL", "qwen-max"),
        help="Model name for the OpenAI-compatible API",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(r"C:\OSWorld\Microsoft\atomic_task_preview.json"),
        help="Path to save generated atomic tasks in single mode",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(r"C:\OSWorld\Microsoft"),
        help="Directory to save generated atomic task files in batch mode",
    )
    args = parser.parse_args()

    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise SystemExit("DASHSCOPE_API_KEY is required.")

    questions = load_questions(args.input)
    if args.index < 0 or args.index >= len(questions):
        raise SystemExit(f"Index out of range: {args.index}, total questions: {len(questions)}")
    if args.count <= 0:
        raise SystemExit("--count must be greater than 0")

    end_index = min(args.index + args.count, len(questions))
    selected_items = questions[args.index:end_index]

    dashscope.api_key = api_key

    for offset, item in enumerate(selected_items, start=args.index):
        question = item.get("question", "").strip()
        if not question:
            print(f"Skipping index {offset}: empty question")
            continue

        response = dashscope.Generation.call(
            model=args.model,
            temperature=0.2,
            top_p=0.8,
            result_format="message",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question)},
            ],
        )

        if response.status_code != 200:
            raise SystemExit(
                f"DashScope request failed at index {offset}: status={response.status_code}, "
                f"code={getattr(response, 'code', None)}, message={getattr(response, 'message', None)}"
            )

        content = response["output"]["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        output = {
            "source_file": item.get("file_name"),
            "source_id": item.get("id"),
            "source_question": question,
            "atomic_tasks": parsed.get("atomic_tasks", []),
            "model": args.model,
            "index": offset,
        }

        if args.count == 1:
            output_path = args.output
        else:
            file_stem = Path(item.get("file_name", f"item_{offset}.txt")).stem
            output_path = args.output_dir / f"atomic_task_preview_{file_stem}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
