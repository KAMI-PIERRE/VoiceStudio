"""Presentation layer for the local character voice studio.

The synthesis engine is injected so importing this module never loads a model.
"""

from collections.abc import Callable, Mapping
import base64
from functools import lru_cache
from html import escape
import math
from pathlib import Path
import re

import gradio as gr

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "voice-studio-logo.svg"


_THEME_VALUES = {
    "body_background_fill": "#f6f4ef",
    "body_text_color": "#232334",
    "body_text_color_subdued": "#6b687b",
    "background_fill_primary": "#ffffff",
    "background_fill_secondary": "#f6f4ef",
    "block_background_fill": "#ffffff",
    "block_border_color": "#e7e3dc",
    "block_label_background_fill": "transparent",
    "block_label_text_color": "#413d54",
    "block_title_background_fill": "transparent",
    "block_title_text_color": "#413d54",
    "input_background_fill": "#fbfaf7",
    "input_border_color": "#e7e3dc",
    "input_border_color_focus": "#7961cc",
    "input_shadow": "none",
    "input_shadow_focus": "0 0 0 3px rgba(121,97,204,0.12)",
    "button_primary_background_fill": "#6d50bc",
    "button_primary_background_fill_hover": "#5d40a6",
    "button_primary_text_color": "#ffffff",
    "button_secondary_background_fill": "#ffffff",
    "button_secondary_background_fill_hover": "#f2edf9",
    "button_secondary_text_color": "#413d54",
    "button_secondary_border_color": "#e7e3dc",
    "checkbox_label_background_fill": "#fbfaf7",
    "checkbox_label_background_fill_hover": "#f6f1ff",
    "checkbox_label_background_fill_selected": "#f0eafb",
    "checkbox_label_border_color": "#e7e3dc",
    "checkbox_label_border_color_selected": "#7961cc",
    "checkbox_label_text_color": "#413d54",
    "checkbox_label_text_color_selected": "#473078",
    "border_color_primary": "#e7e3dc",
    "panel_background_fill": "#ffffff",
    "panel_border_color": "#e7e3dc",
}
THEME = gr.themes.Soft(
    primary_hue="violet",
    neutral_hue="stone",
    radius_size="lg",
    font=["Segoe UI", "Arial", "sans-serif"],
    font_mono=["Consolas", "monospace"],
).set(
    **_THEME_VALUES,
    **{f"{key}_dark": value for key, value in _THEME_VALUES.items()},
    block_border_width="1px",
    block_label_padding="0",
    block_label_margin="0 0 8px 0",
    button_primary_shadow="none",
    button_secondary_shadow="none",
    checkbox_label_shadow="none",
)

CSS = """
body { background: #f6f4ef; }
.gradio-container {
    max-width: 1280px !important;
    width: 100% !important;
    margin: 0 auto !important;
    padding: 0 0 28px !important;
    color: #232334;
    font-family: "Segoe UI", Arial, sans-serif !important;
}
.main { padding: 16px 0 !important; }
.studio-shell { gap: 24px !important; padding: 26px 36px 0; }
.studio-navigation {
    display: flex; align-items: center; justify-content: space-between;
    gap: 18px; padding-bottom: 24px; border-bottom: 1px solid #e3dfd8;
}
.studio-brand { display: flex; align-items: center; gap: 11px; }
.studio-brand strong { font-size: 17px; letter-spacing: -0.4px; }
.studio-brand small { display: block; color: #827a92; font-size: 11px; margin-top: 2px; }
.studio-mark {
    display: block; flex: 0 0 44px; width: 44px; height: 44px; object-fit: contain;
}
.studio-badge {
    display: inline-flex; align-items: center; gap: 7px; font-size: 12px;
    color: #5c5869; background: #eeece5; padding: 8px 12px; border-radius: 30px;
}
.studio-badge::before { content: ""; width: 6px; height: 6px; background: #52836c; border-radius: 50%; }
.studio-intro {
    display: flex; align-items: flex-end; justify-content: space-between;
    padding: 5px 0 3px; gap: 24px;
}
.studio-eyebrow { color: #79638e; font-size: 10px; font-weight: 700; letter-spacing: 2px; margin-bottom: 10px; }
.studio-intro h1 { margin: 0; font-size: clamp(30px, 3.6vw, 44px); font-weight: 650; line-height: 1.16; letter-spacing: -1.6px; color: #232334; }
.studio-intro p { color: #716b7b; font-size: 14px; line-height: 1.7; margin: 12px 0 0; max-width: 540px; }
.studio-voice-count { color: #6d50bc; text-align: right; white-space: nowrap; padding-bottom: 5px; }
.studio-voice-count strong { display: block; font-size: 28px; line-height: 1.2; font-weight: 650; letter-spacing: -1px; }
.studio-voice-count span { font-size: 11px; color: #827a92; }
.workspace-row { gap: 22px !important; align-items: flex-start; }
.workspace-column { gap: 20px !important; min-width: 0 !important; }
.studio-panel {
    background: #fff; border: 1px solid #e7e3dc; border-radius: 18px;
    padding: 22px !important; gap: 16px !important;
    box-shadow: 0 3px 14px rgba(52,38,64,0.025);
}
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
.panel-title { display: flex; align-items: center; gap: 10px; }
.panel-title h2 { margin: 0; color: #292536; font-size: 17px; font-weight: 650; letter-spacing: -0.3px; }
.panel-number { display: flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 8px; background: #f2edf9; color: #8368b6; font-size: 10px; font-weight: 650; }
.panel-note { color: #877e94; font-size: 11px; }
.panel-description { margin: -4px 0 0; color: #7d7588; font-size: 12px; line-height: 1.6; }
#script-editor { background: #fbfaf7; border-color: #e7e3dc; border-radius: 12px; }
#script-editor textarea {
    min-height: 290px; padding: 18px !important; line-height: 1.8;
    color: #373044; font-size: 15px; resize: vertical;
}
#script-editor textarea::placeholder { color: #a198aa; }
.script-statistics { display: flex; align-items: center; justify-content: space-between; gap: 10px; color: #898092; font-size: 11px; }
.script-statistics strong { color: #655c72; font-weight: 550; }
.script-statistics .over-limit { color: #b03e52; }
.script-meter { height: 3px; overflow: hidden; background: #efede8; border-radius: 4px; margin-top: 10px; }
.script-meter span { display: block; height: 100%; background: #ba9ce4; border-radius: inherit; transition: width 160ms ease; }
.sample-heading { color: #8b8198; font-size: 10px; letter-spacing: 1.4px; font-weight: 650; margin-top: 3px; }
.sample-row { gap: 8px !important; flex-wrap: wrap !important; }
.sample-row button { min-width: 0 !important; padding: 8px 10px !important; border: 1px solid #e7e3dc !important; border-radius: 8px !important; font-size: 11px !important; box-shadow: none !important; }
.sample-row .clear-script { border-color: transparent !important; color: #8b8198 !important; background: transparent !important; }
#generate-speech { min-height: 48px; border-radius: 10px; font-size: 14px; font-weight: 650; letter-spacing: 0.1px; }
.generate-note { color: #93899e; text-align: center; font-size: 10px; line-height: 1.6; margin-top: -6px; }
#character-choices { border: 0 !important; padding: 0 !important; background: transparent !important; box-shadow: none !important; }
#character-choices .wrap { display: grid !important; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px !important; }
#character-choices .wrap label {
    position: relative; align-items: center; min-width: 0; min-height: 80px; padding: 10px !important;
    border: 1px solid #e7e3dc !important; border-radius: 10px !important;
    background: #fbfaf7 !important; box-shadow: none !important; gap: 8px;
    transition: background 140ms ease, border-color 140ms ease;
}
#character-choices .wrap label::before {
    content: ""; display: block; flex: 0 0 38px; width: 38px; height: 38px;
    border-radius: 50%; background-color: #e8e1f1; background-size: cover;
    background-position: center; border: 2px solid #fff;
    box-shadow: 0 1px 4px rgba(52,38,64,0.06);
}
#character-choices .wrap label:hover { background: #f7f2ff !important; border-color: #c4b4df !important; transform: none !important; }
#character-choices .wrap label.selected,
#character-choices .wrap label:has(input:checked) { border-color: #9777ce !important; background: #f0eafb !important; color: #473078 !important; }
#character-choices .wrap label span {
    white-space: pre-line; line-height: 1.6; color: #82768e; font-size: 10px;
    overflow-wrap: anywhere; margin-left: 0 !important; flex: 1; min-width: 0; padding-right: 4px;
}
#character-choices .wrap label span::first-line { font-size: 13px; color: #40304f; font-weight: 650; }
#character-choices input[type="radio"] { position: absolute; top: 5px; right: 5px; min-width: 10px; width: 10px; height: 10px; accent-color: #7961cc; }
#character-choices .wrap label:focus-within { outline: 2px solid #7961cc; outline-offset: 2px; }
.selected-character {
    display: flex; align-items: flex-start; gap: 13px; padding: 16px;
    border-radius: 12px; background: #f7f3fc; border: 1px solid #ece4f6;
}
.character-avatar {
    display: block; flex: 0 0 48px; width: 48px; height: 48px; border-radius: 50%;
    object-fit: cover; border: 2px solid #fff; box-shadow: 0 2px 6px rgba(52,38,64,0.08);
}
.character-selected-label { font-size: 9px; letter-spacing: 1.1px; color: #95849f; font-weight: 650; text-transform: uppercase; margin-bottom: 4px; }
.character-name { color: #473552; font-size: 14px; font-weight: 650; }
.character-name span { color: #9787a1; font-size: 11px; font-weight: 400; margin-left: 5px; }
.character-description { color: #82718e; font-size: 11px; margin: 6px 0 0; line-height: 1.6; }
#preview-voice { border: 1px solid #ddd1ee; background: #faf7ff; color: #6d50bc; border-radius: 9px; font-size: 12px; min-height: 38px; box-shadow: none; }
#preview-voice:hover { background: #f0eafb; }
.settings-heading { color: #8b8198; font-size: 10px; letter-spacing: 1.4px; font-weight: 650; padding-top: 2px; }
.voice-slider { border: 0 !important; background: transparent !important; padding: 0 !important; box-shadow: none !important; }
.voice-slider input[type="number"] { font-size: 11px !important; color: #77648c !important; background: #f7f3fc !important; border: 0 !important; border-radius: 6px !important; }
.voice-slider .info { color: #978b9e !important; font-size: 10px !important; }
.render-panel { padding-bottom: 20px !important; }
#speech-output { border-radius: 12px !important; background: #fbfaf7 !important; border-color: #e7e3dc !important; }
#speech-download { border-radius: 10px !important; background: #fbfaf7 !important; border-color: #e7e3dc !important; min-height: 88px; max-height: 100px; overflow: auto; }
#speech-download .empty { min-height: 68px !important; height: 68px !important; }
#speech-status { color: #817589; font-size: 12px; line-height: 1.6; }
#speech-status p { margin: 0; }
#speech-status strong { color: #594c69; }
.studio-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; font-size: 10px; color: #9c929f; padding: 0 2px 5px; }
.developer-credit { padding: 20px 12px 8px; border-top: 1px solid #e3dfd8; text-align: center; color: #817589; font-size: 12px; line-height: 1.8; }
.developer-credit p { margin: 0; }
.developer-credit a { color: #6d50bc; font-weight: 650; text-decoration: none; }
.developer-credit a:hover { text-decoration: underline; text-underline-offset: 3px; }
.developer-credit a:focus-visible { outline: 2px solid #7961cc; outline-offset: 4px; border-radius: 3px; }
.developer-role { color: #8b8198; }
@media (max-width: 900px) {
    .studio-shell { padding: 26px 22px 0; }
    .workspace-row { flex-direction: column !important; }
    .workspace-row > .workspace-column { width: 100% !important; flex: auto !important; }
    .workspace-row > .character-column { order: -1; }
    #character-choices .wrap { grid-template-columns: repeat(3,minmax(0,1fr)); }
    .studio-intro h1 { font-size: 35px; }
}
@media (max-width: 540px) {
    .studio-shell { padding: 18px 14px 0; gap: 18px !important; }
    .studio-navigation { padding-bottom: 18px; }
    .studio-badge { font-size: 10px; padding: 7px 10px; }
    .studio-brand small { display: none; }
    .studio-intro { align-items: flex-start; }
    .studio-intro h1 { font-size: 30px; letter-spacing: -1.2px; }
    .studio-intro p { font-size: 12px; }
    .studio-voice-count { display: none; }
    .studio-panel { padding: 17px !important; }
    #character-choices .wrap { grid-template-columns: repeat(2,minmax(0,1fr)); }
    #script-editor textarea { min-height: 250px; padding: 14px !important; font-size: 14px; }
    .script-statistics { align-items: flex-start; font-size: 10px; }
    .sample-row { display: grid !important; grid-template-columns: repeat(2,minmax(0,1fr)); }
    .sample-row button { min-width: 0 !important; width: 100%; }
    .studio-footer { flex-direction: column; gap: 5px; align-items: flex-start; }
    .developer-credit { font-size: 11px; }
    .developer-role { display: block; }
    .developer-separator { display: none; }
}
@media (prefers-reduced-motion: reduce) {
    #character-choices .wrap label, .script-meter span { transition: none; }
}
"""

SAMPLE_SCRIPTS = {
    "Story": (
        "The little bookshop was the last place Maya expected to find an adventure. "
        "But on a rainy Tuesday, a letter slipped from the pages of an old atlas. "
        "It contained just six words: The island is waiting for you. "
        "She smiled, folded the letter carefully, and began to pack."
    ),
    "Presentation": (
        "Good morning, everyone. Today, we are introducing a simpler way to turn ideas "
        "into action. Our goal is clear: help people spend less time on routine tasks "
        "and more time on the work that matters. Let's start with the opportunity, "
        "then walk through our plan together."
    ),
    "Advertisement": (
        "Make room for a brighter morning. With freshly roasted coffee and a moment "
        "to yourself, an ordinary day becomes something special. Discover your new "
        "favorite blend today. One small ritual. A whole new start."
    ),
}


def script_statistics(text: str, speed: float, pause_ms: int, max_characters: int) -> str:
    """Return escaped, accessible script counters and an approximate duration."""
    text = text or ""
    count = len(text)
    words = len(text.split())
    sentences = max(0, len(re.findall(r"[.!?]+(?:\s|$)", text)) - 1)
    seconds = math.ceil(words * 60 / (165 * max(float(speed), 0.01)) + sentences * float(pause_ms) / 1000)
    duration = f"{seconds // 60}:{seconds % 60:02d}"
    fill = min(100, count * 100 / max(1, max_characters))
    limit_class = " class='over-limit'" if count > max_characters else ""
    return (
        "<div aria-live='polite' aria-atomic='true'>"
        "<div class='script-statistics'>"
        f"<span{limit_class}><strong>{count:,}</strong> / {max_characters:,} characters</span>"
        f"<span>{words:,} words &nbsp;·&nbsp; About <strong>{duration}</strong></span>"
        "</div>"
        f"<div class='script-meter' aria-hidden='true'><span style='width:{fill:.2f}%'></span></div>"
        "</div>"
    )


@lru_cache(maxsize=32)
def avatar_uri(filename: str) -> str:
    """Embed local portraits so the interface also renders without an internet connection."""
    if not re.fullmatch(r"[a-z]+\.svg", filename):
        return ""
    path = Path(__file__).resolve().parent / "assets" / "avatars" / filename
    if not path.is_file():
        return ""
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def character_profile(character: Mapping[str, str]) -> str:
    """Render trusted catalog metadata with escaping for every text field."""
    color = str(character.get("color", "#8d72bb"))
    if not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", color):
        color = "#8d72bb"
    name = escape(str(character.get("name", "Character")))
    portrait = avatar_uri(str(character.get("avatar", "")))
    avatar = (
        f"<img class='character-avatar' src='{portrait}' alt='{name} character avatar' width='48' height='48'>"
        if portrait else
        f"<span class='character-avatar' style='background:{color}' aria-hidden='true'>{escape(str(character.get('initials', name[:2])).upper())}</span>"
    )
    role = escape(str(character.get("role", "")))
    description = escape(str(character.get("description", "")))
    voice_label = escape(str(character.get("voice_label", "English")))
    return (
        "<div class='selected-character' aria-live='polite'>"
        f"{avatar}"
        "<div><div class='character-selected-label'>Selected character</div>"
        f"<div class='character-name'>{name}<span>· {role}</span></div>"
        f"<p class='character-description'>{description}<br>{voice_label}</p></div></div>"
    )


def _heading(number: str, title: str, note: str = "") -> str:
    return (
        "<div class='panel-heading'><div class='panel-title'>"
        f"<span class='panel-number'>{escape(number)}</span><h2>{escape(title)}</h2></div>"
        f"<span class='panel-note'>{escape(note)}</span></div>"
    )


def build_interface(
    synthesize: Callable,
    characters: Mapping[str, Mapping[str, str]],
    default_character: str,
    max_characters: int,
    engine_label: str,
    hosted: bool = False,
    retention_seconds: int = 0,
) -> gr.Blocks:
    """Build the studio; callers pass ``THEME`` and ``CSS`` to ``launch``."""
    if not characters or default_character not in characters:
        raise ValueError("The character catalog must include the default character.")
    if max_characters < 1:
        raise ValueError("The script character limit must be positive.")
    logo_source = "data:image/svg+xml;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")

    initial_script = (
        "Every great idea starts with a story. Choose a voice, add your words, "
        "and bring your next story to life. Welcome to Voice Studio."
    )
    # Sample text remains valid when a caller uses a smaller script limit.
    initial_script = initial_script[:max_characters]
    choices = [
        (f"{character['name']}\n{character.get('voice_label', 'English')}", slug)
        for slug, character in characters.items()
    ]

    cache_policy = (600, retention_seconds) if hosted and retention_seconds else None
    if hosted and retention_seconds:
        hours = retention_seconds / 3600
        recording_note = f"Download your recording to keep it. Hosted recordings expire after {hours:g} hours."
    elif hosted:
        recording_note = "Download your recording to keep a copy. Your script is processed on the server."
    else:
        recording_note = "First use downloads the voice library. Later recordings work offline."
    with gr.Blocks(title="Voice Studio · Character voices", analytics_enabled=False, delete_cache=cache_policy) as demo:
        with gr.Column(elem_classes=["studio-shell"]):
            gr.HTML(
                "<header class='studio-navigation'>"
                "<div class='studio-brand'>"
                f"<img class='studio-mark' src='{logo_source}' alt='Voice Studio logo' width='44' height='44'>"
                "<div><strong>Voice Studio</strong><small>A little character. A lot of possibility.</small></div></div>"
                f"<span class='studio-badge'>{escape(engine_label)}</span></header>"
            )
            gr.HTML(
                "<div class='studio-intro'><div>"
                "<div class='studio-eyebrow'>MAKE EVERY WORD YOURS</div>"
                "<h1>Bring your words to life.</h1>"
                "<p>Find the character that fits your story. Write your script, shape the pace, "
                "and create speech you can listen to and keep.</p></div>"
                f"<div class='studio-voice-count'><strong>{len(characters):02d}</strong><span>distinct voices to explore</span></div></div>"
            )
            with gr.Row(elem_classes=["workspace-row"], equal_height=False):
                with gr.Column(scale=7, min_width=390, elem_classes=["workspace-column"]):
                    with gr.Column(elem_classes=["studio-panel"]):
                        gr.HTML(_heading("01", "Your script", "Start with an idea"))
                        script = gr.Textbox(
                            label="Script to read aloud",
                            show_label=False,
                            placeholder="Type or paste your English script here…",
                            value=initial_script,
                            lines=11,
                            max_lines=25,
                            max_length=max_characters,
                            elem_id="script-editor",
                            html_attributes={"aria-label": "Script to read aloud"},
                        )
                        statistics = gr.HTML(script_statistics(initial_script, 1.0, 220, max_characters))
                        gr.HTML("<div class='sample-heading'>NEED A STARTING POINT?</div>")
                        sample_buttons = []
                        with gr.Row(elem_classes=["sample-row"]):
                            for label, sample in SAMPLE_SCRIPTS.items():
                                sample_buttons.append((gr.Button(label, size="sm", min_width=90), sample[:max_characters]))
                            clear = gr.Button("Clear script", size="sm", min_width=90, elem_classes=["clear-script"])
                        generate = gr.Button(
                            f"Generate speech · {characters[default_character]['name']}",
                            variant="primary",
                            size="lg",
                            elem_id="generate-speech",
                        )
                        gr.HTML(f"<div class='generate-note'>{escape(recording_note)}</div>")
                    with gr.Column(elem_classes=["studio-panel", "render-panel"]):
                        gr.HTML(_heading("03", "Your recording", "Listen. Download. Share."))
                        audio = gr.Audio(
                            label="Speech recording",
                            show_label=False,
                            type="filepath",
                            format="wav",
                            interactive=False,
                            editable=False,
                            elem_id="speech-output",
                        )
                        status = gr.Markdown(
                            "Ready when you are. Choose a character and generate your first take.",
                            elem_id="speech-status",
                        )
                        download = gr.File(label="Download WAV", interactive=False, height=88, elem_id="speech-download")
                with gr.Column(scale=4, min_width=340, elem_classes=["workspace-column", "character-column"]):
                    with gr.Column(elem_classes=["studio-panel"]):
                        gr.HTML(_heading("02", "Choose a character", f"{len(characters)} voices"))
                        gr.HTML("<p class='panel-description'>Different characters. Distinct voices. Find your favorite.</p>")
                        character = gr.Radio(
                            choices=choices,
                            value=default_character,
                            label="Character voice",
                            show_label=False,
                            interactive=True,
                            elem_id="character-choices",
                        )
                        selected_profile = gr.HTML(character_profile(characters[default_character]))
                        preview_button = gr.Button("Preview this voice", elem_id="preview-voice", size="sm")
                        gr.HTML("<div class='settings-heading'>FINE-TUNE THE DELIVERY</div>")
                        speed = gr.Slider(
                            minimum=0.75,
                            maximum=1.5,
                            value=1.0,
                            step=0.05,
                            label="Speaking speed",
                            info="1.0 is natural speed. Lower is slower.",
                            elem_classes=["voice-slider"],
                        )
                        pause = gr.Slider(
                            minimum=0,
                            maximum=1000,
                            value=220,
                            step=20,
                            label="Pause between sections (ms)",
                            info="Adds a pause between sentences and longer script sections.",
                            elem_classes=["voice-slider"],
                        )
            gr.HTML(
                "<footer class='studio-footer'><span>Made for stories, presentations, and everyday ideas.</span>"
                f"<span>English voices · Up to {max_characters:,} characters per take</span></footer>"
                "<div class='developer-credit'><p>Developed by "
                "<a href='https://kamipierre.vercel.app/' target='_blank' rel='noopener noreferrer'>KAMI Pierre</a>"
                "<span class='developer-separator'> · </span>"
                "<span class='developer-role'>Full-stack System Developer</span></p></div>"
            )

        def update_script_details(text: str, speaking_speed: float, pause_ms: int) -> str:
            return script_statistics(text, speaking_speed, pause_ms, max_characters)

        def select_character(character_id: str):
            selected = characters[character_id]
            return character_profile(selected), gr.update(value=f"Generate speech · {selected['name']}")

        def preview_voice(character_id: str, speaking_speed: float, pause_ms: int, progress=gr.Progress()):
            preview_script = "Hello. This is a preview of my voice. Let me help bring your next story to life."
            preview_audio, preview_download, metadata = synthesize(
                preview_script, character_id, speaking_speed, pause_ms, progress=progress
            )
            return preview_audio, preview_download, f"**Voice preview** · {metadata}"

        for control in [script, speed, pause]:
            control.change(
                update_script_details,
                inputs=[script, speed, pause],
                outputs=statistics,
                queue=False,
                api_visibility="private",
                show_progress="hidden",
            )
        character.change(
            select_character,
            inputs=character,
            outputs=[selected_profile, generate],
            queue=False,
            api_visibility="private",
            show_progress="hidden",
        )
        for button, sample in sample_buttons:
            button.click(lambda value=sample: value, outputs=script, queue=False, api_visibility="private")
        clear.click(lambda: "", outputs=script, queue=False, api_visibility="private")
        generate.click(
            synthesize,
            inputs=[script, character, speed, pause],
            outputs=[audio, download, status],
            api_name="synthesize",
            api_description="Generate an English speech recording with your chosen character voice.",
            concurrency_limit=1,
            concurrency_id="speech",
            show_progress="full",
            show_progress_on=[audio, status],
        )
        preview_button.click(
            preview_voice,
            inputs=[character, speed, pause],
            outputs=[audio, download, status],
            api_name="preview_voice",
            api_description="Hear a short preview of your chosen character voice.",
            concurrency_limit=1,
            concurrency_id="speech",
            show_progress="full",
            show_progress_on=[audio, status],
        )
    return demo


def _avatar_styles():
    from characters import CHARACTERS
    rules = []
    for index, character in enumerate(CHARACTERS.values(), start=1):
        portrait = avatar_uri(character["avatar"])
        if portrait:
            rules.append(
                f"#character-choices .wrap label:nth-of-type({index})::before "
                f"{{ background-image: url('{portrait}'); }}"
            )
    return "\n".join(rules)


CSS += "\n" + _avatar_styles()
