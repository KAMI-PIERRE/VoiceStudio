"""The studio's distinct English speakers and their presentation metadata."""

DEFAULT_CHARACTER = "heart"


def _character(name, role, description, voice, color, british=False):
    gender = "Feminine" if voice[1] == "f" else "Masculine"
    accent = "British" if british else "American"
    return {
        "name": name,
        "role": role,
        "description": description,
        "voice": voice,
        "voice_label": f"{accent} · {gender}",
        "language": "en-gb" if british else "en-us",
        "color": color,
        "initials": name[:2].upper(),
        "avatar": f"{name.lower()}.svg",
        "gender": gender,
    }


CHARACTERS = {
    "heart": _character("Heart", "Everyday narrator", "A versatile voice for introductions, everyday stories, and clear narration.", "af_heart", "#7756df"),
    "bella": _character("Bella", "Content creator", "Try Bella for video scripts, product introductions, and short creative pieces.", "af_bella", "#cb6c83"),
    "nicole": _character("Nicole", "Storyteller", "A distinct voice to explore for intimate stories and character dialogue.", "af_nicole", "#62887a"),
    "sarah": _character("Sarah", "Presenter", "A voice to try for presentations, explanations, and learning materials.", "af_sarah", "#c48d46"),
    "sky": _character("Sky", "Friendly guide", "Try Sky for friendly welcome messages, walkthroughs, and short updates.", "af_sky", "#678eac"),
    "adam": _character("Adam", "Announcer", "A masculine voice for announcements, introductions, and narration.", "am_adam", "#786496"),
    "michael": _character("Michael", "Podcast host", "Try Michael for conversational scripts, interviews, and podcast introductions.", "am_michael", "#6e8392"),
    "fenrir": _character("Fenrir", "Adventure narrator", "An alternative masculine voice for creative stories and imaginative scripts.", "am_fenrir", "#9b7960"),
    "emma": _character("Emma", "British narrator", "A British voice to explore for audiobooks, introductions, and polished narration.", "bf_emma", "#798358", british=True),
    "isabella": _character("Isabella", "British storyteller", "Try Isabella for British storytelling, personal messages, and narration.", "bf_isabella", "#b57997", british=True),
    "george": _character("George", "Documentary voice", "A British masculine voice for explainers, documentaries, and presentations.", "bm_george", "#617e87", british=True),
    "fable": _character("Fable", "British story guide", "Another British masculine voice for stories, dialogue, and creative narration.", "bm_fable", "#a57b50", british=True),
}
