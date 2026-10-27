import re
from dataclasses import dataclass

from apps.accounts.models import StudentProfile
from apps.assistant import clients
from apps.assistant.services.context import build_student_context
from apps.assistant.services.retrieval import RetrievedChunk, retrieve

_PERSONAL_PRONOUNS = re.compile(r"\b(i|my|me|mine|myself)\b", re.IGNORECASE)

I_DONT_KNOW = "I don't know based on the available information."

PERSONAL_DATA_UNAVAILABLE = (
    "I can't answer questions involving your personal records right now because "
    "a privacy-verified AI configuration isn't set up. Please contact IT support."
)

SYSTEM_PROMPT = (
    "You are the university's campus assistant. Answer ONLY using the numbered "
    "context sections provided below. Cite the sections you used inline like "
    "[1], [2]. If the context does not contain the answer, respond with exactly "
    f"this sentence and nothing else, with no quotation marks: {I_DONT_KNOW}"
)

@dataclass(frozen=True)
class Source:
    title: str
    document_id: int | None = None
    chunk_id: int | None = None


@dataclass(frozen=True)
class Answer:
    text: str
    sources: list[Source]
    grounded: bool


def _build_prompt(*, question: str, chunks: list[RetrievedChunk], personal) -> str:
    sections = []
    for i, chunk in enumerate(chunks, start=1):
        sections.append(f"[{i}] ({chunk.document_title})\n{chunk.content}")
    if personal is not None:
        sections.append(f"[{len(chunks) + 1}] ({personal.label})\n{personal.text}")
    context = "\n\n".join(sections)
    return f"Context:\n{context}\n\nQuestion: {question}"


def _declined(text: str) -> bool:
    """True if the LLM's reply is blank, or is the I_DONT_KNOW decline (allowing
    for models that wrap it in quote marks despite being told not to) - this is
    only a secondary guard; the primary defense against citing irrelevant
    chunks is the distance floor in selectors.search_chunks."""
    normalized = text.strip(" \t\r\n\"'“”‘’")
    return not normalized or normalized == I_DONT_KNOW


def is_personal_question(question: str) -> bool:
    """Whether a question is phrased about the asker themselves (first-person
    pronouns), used to decide whether a student's own record is worth
    attaching as context - a plain keyword heuristic, not a guarantee. Kept
    deliberately separate from apps.portal.intents.detect_intent: that router
    picks one of a few specific template-answerable categories; this is a
    coarser signal shared by every caller (this module's own callers included)
    to gate personal-context injection into an LLM prompt."""
    return bool(_PERSONAL_PRONOUNS.search(question))


def answer_question(
    *, question: str, student: StudentProfile | None = None, include_personal_context: bool = False
) -> Answer:
    chunks = retrieve(query=question)
    # An attached StudentProfile is not, by itself, grounding: it only counts
    # once the question is actually about the student (include_personal_context)
    # - otherwise build_student_context would get injected into every prompt a
    # logged-in user ever sends, regardless of relevance.
    has_personal_signal = include_personal_context and student is not None
    personal = build_student_context(student=student) if has_personal_signal else None

    if not chunks and not has_personal_signal:
        return Answer(text=I_DONT_KNOW, sources=[], grounded=False)

    # The training-eligibility gate tracks whether personal data will actually
    # land in the prompt (has_personal_signal), not whether a session happens
    # to be attached: a logged-in student asking something with no personal
    # data in it is exactly as safe to send to the free client as an
    # anonymous question - only an actual injection of build_student_context
    # requires the verified non-training client.
    allow_training = not has_personal_signal

    try:
        llm = clients.get_llm_client(allow_training=allow_training)
    except clients.NonTrainingUnavailable:
        return Answer(text=PERSONAL_DATA_UNAVAILABLE, sources=[], grounded=False)

    prompt = _build_prompt(question=question, chunks=chunks, personal=personal)
    response = llm.generate(system=SYSTEM_PROMPT, prompt=prompt)

    if _declined(response.text):
        # The LLM declined despite having candidate context (e.g. retrieval
        # returned only weakly-related chunks) - don't cite them as sources.
        return Answer(text=I_DONT_KNOW, sources=[], grounded=False)

    sources = [
        Source(title=chunk.document_title, document_id=chunk.document_id, chunk_id=chunk.chunk_id)
        for chunk in chunks
    ]
    if personal is not None:
        sources.append(Source(title=personal.label))

    return Answer(text=response.text, sources=sources, grounded=True)
