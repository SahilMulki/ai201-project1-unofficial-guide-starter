"""
Milestone 5 — Gradio Web Interface

Launch:
  .venv/bin/python app.py
  # then open http://127.0.0.1:7860 in your browser
"""

import gradio as gr
from query import ask

# Optional: let the user narrow to a specific course so retrieval is tighter.
# Leave blank to search the full corpus.
COURSE_HINT = (
    "Optional: narrow to a specific course (e.g. CMSC131). "
    "Leave blank to search everything."
)


def handle_query(question: str, course_filter: str) -> tuple[str, str]:
    if not question.strip():
        return "Please enter a question.", ""

    where = None
    course = course_filter.strip().upper()
    if course:
        where = {"course": course}

    try:
        result = ask(question, where=where)
    except Exception as e:
        return f"Error: {e}", ""

    answer = result["answer"]
    sources_text = "\n".join(f"• {s}" for s in result["sources"])
    if not sources_text:
        sources_text = "(no sources attributed)"

    return answer, sources_text


# ── UI layout ────────────────────────────────────────────────────────────────

with gr.Blocks(title="The Unofficial Guide — UMD") as demo:
    gr.Markdown(
        """
        # The Unofficial Guide — UMD
        Get course and professor recommendations powered by PlanetTerp reviews
        and the UMD Gen Ed requirements PDF.

        > **Grounding guarantee:** answers come only from retrieved documents.
        > If the knowledge base doesn't cover your question, the guide will say so.
        """
    )

    with gr.Row():
        with gr.Column(scale=3):
            question_box = gr.Textbox(
                label="Your question",
                placeholder="e.g. Who is the best professor for CMSC131?",
                lines=2,
            )
        with gr.Column(scale=1):
            course_box = gr.Textbox(
                label="Course filter (optional)",
                placeholder="e.g. CMSC131",
                info=COURSE_HINT,
            )

    ask_btn = gr.Button("Ask", variant="primary")

    answer_box = gr.Textbox(label="Answer", lines=10, interactive=False)
    sources_box = gr.Textbox(label="Retrieved from", lines=5, interactive=False)

    # Example queries users can click to pre-fill
    gr.Examples(
        examples=[
            ["Who is the most recommended professor for CMSC131?", "CMSC131"],
            ["How hard is CMSC351 Algorithms? What do students say?", "CMSC351"],
            ["What Gen Ed Distributive Studies categories do I need to complete?", ""],
            ["What do premed students say about chemistry courses at UMD?", ""],
            ["Which CMSC professors have the best student ratings?", ""],
            ["What is the average rent near UMD campus?", ""],  # grounding failure test
        ],
        inputs=[question_box, course_box],
        label="Try these questions",
    )

    ask_btn.click(
        handle_query,
        inputs=[question_box, course_box],
        outputs=[answer_box, sources_box],
    )
    question_box.submit(
        handle_query,
        inputs=[question_box, course_box],
        outputs=[answer_box, sources_box],
    )

if __name__ == "__main__":
    demo.launch()
