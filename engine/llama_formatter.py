import os
import re
from typing import Optional
import config

class LlamaFormatter:
    """
    Offline Text Polishing & Smart Flow Post-Processing.
    Supports:
    1. Built-in ultra-fast offline phonetic & disfluency cleaning engine.
    2. Local LLaMA GGUF integration via llama-cpp-python or local Ollama when present.
    """

    def __init__(self, mode: str = config.DEFAULT_FLOW_MODE):
        self.mode = mode
        self._llm = None
        self._try_init_local_llm()

    def _try_init_local_llm(self):
        """Attempt to load local LLaMA model if GGUF exists in models directory."""
        llama_path = config.LLAMA_MODEL_PATH
        if os.path.exists(llama_path):
            try:
                from llama_cpp import Llama
                print(f"[LlamaFormatter] Loading local LLaMA GGUF from {llama_path}...")
                self._llm = Llama(
                    model_path=llama_path,
                    n_ctx=1024,
                    n_threads=4,
                    verbose=False
                )
                print("[LlamaFormatter] Local LLaMA loaded successfully!")
            except Exception as e:
                print(f"[LlamaFormatter] Note: llama-cpp not loaded ({e}). Using native Smart Flow engine.")

    def format_text(self, text: str, mode: Optional[str] = None) -> str:
        """Process and format transcribed text according to the selected mode."""
        if not text or not text.strip():
            return ""

        current_mode = mode or self.mode

        if current_mode == "raw":
            return text.strip()

        # If local LLaMA is loaded, pass through LLaMA prompt
        if self._llm is not None:
            formatted = self._llm_format(text, current_mode)
            if formatted:
                return formatted

        # Native Smart Flow Engine (ultra-fast, zero-overhead, 100% offline)
        return self._native_smart_flow(text, current_mode)

    def _native_smart_flow(self, text: str, mode: str) -> str:
        t = text.strip()

        # 1. Strip vocal disfluencies & filler sounds
        fillers = [
            r"\b(um|uh|er|ah|umm|uhh)\b[,.]?",
            r"\b(you know|I mean|sort of|kind of)\b,",
            r"\b(like)\b(?=\s+(um|uh|basically|literally))",
            r"\b([a-zA-Z]+)\s+\1\b"  # Repetitive stutter words (e.g. "the the")
        ]
        for pattern in fillers:
            t = re.sub(pattern, "", t, flags=re.IGNORECASE)

        # 2. Spoken punctuation & structural commands
        punct_map = [
            (r"\bnew line\b", "\n"),
            (r"\bnext line\b", "\n"),
            (r"\bnew paragraph\b", "\n\n"),
            (r"\bcomma\b", ","),
            (r"\bperiod\b", "."),
            (r"\bfull stop\b", "."),
            (r"\bquestion mark\b", "?"),
            (r"\bexclamation mark\b", "!"),
            (r"\bcolon\b", ":"),
            (r"\bsemicolon\b", ";"),
            (r"\bhyphen\b", "-"),
            (r"\bdash\b", " - "),
            (r"\bopen quote\b", '"'),
            (r"\bclose quote\b", '"'),
            (r"\bbullet point\b", "\n• "),
            (r"\bbullet\b", "\n• ")
        ]
        for pattern, replacement in punct_map:
            t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)

        # 3. Clean spacing around punctuation
        t = re.sub(r"\s+([,.:;?!])", r"\1", t)
        t = re.sub(r"\s+", " ", t).strip()
        # Restore newlines that were collapsed
        t = t.replace(" \n ", "\n").replace(" \n", "\n").replace("\n ", "\n")

        # 4. Mode-specific adjustments
        if mode == "developer":
            # Code mode formatting
            t = re.sub(r"\bfunction\s+([a-zA-Z_0-9]+)\b", r"def \1():", t)
            t = re.sub(r"\b(const|let|var)\s+([a-zA-Z_0-9]+)\b", r"\1 \2 =", t)
            t = re.sub(r"\bbackticks?\b", "`", t, flags=re.IGNORECASE)
            t = re.sub(r"\btriple backticks?\b", "```", t, flags=re.IGNORECASE)
            t = re.sub(r"\btrue\b", "True", t, flags=re.IGNORECASE)
            t = re.sub(r"\bfalse\b", "False", t, flags=re.IGNORECASE)
            t = re.sub(r"\bnull\b", "None", t, flags=re.IGNORECASE)
        elif mode == "email":
            # Email greetings
            t = re.sub(r"^(hi|hey|hello|dear)\s+([a-zA-Z]+)", r"\1 \2,\n\n", t, flags=re.IGNORECASE)
            t = re.sub(r"\b(best regards|thanks|thank you|sincerely)\b", r"\n\n\1,", t, flags=re.IGNORECASE)

        # 5. Sentence Capitalization
        def capitalize_sentence(match):
            return match.group(1) + match.group(2).upper()

        t = re.sub(r"(^|[.!?\n]\s+)([a-z])", capitalize_sentence, t)

        return t.strip()

    def _llm_format(self, text: str, mode: str) -> Optional[str]:
        """Calls local LLaMA with a strict formatting prompt."""
        try:
            system_prompts = {
                "smart": "You are a professional speech-to-text editor. Your task is to polish raw dictated speech. Remove filler words (um, uh, you know), fix grammar and punctuation, but retain the exact meaning and personal style of the speaker. Output ONLY the polished text without explanation.",
                "developer": "You are an expert software developer speech-to-code transcriber. Format spoken technical sentences into clean developer markdown, camelCase/snake_case variable names, or code snippets where applicable. Output ONLY the polished text.",
                "email": "Format this dictated speech into a clean, polite, and well-structured email message. Output ONLY the resulting text."
            }
            prompt = (
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
                f"{system_prompts.get(mode, system_prompts['smart'])}\n"
                f"<|eot_id|><|start_header_id|>user<|end_header_id|>\n"
                f"Raw Speech: \"{text}\"\n"
                f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
            )
            response = self._llm(prompt, max_tokens=256, stop=["<|eot_id|>"], temperature=0.2)
            return response["choices"][0]["text"].strip()
        except Exception as e:
            print(f"[LlamaFormatter] LLM inference failed, falling back to native: {e}")
            return None
