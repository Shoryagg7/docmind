from core.config import get_settings
from eval.compare_privacy import sign_test_p
from eval.run_eval import is_refusal
from services import llm_client
from tests.test_privacy import FakeGroq


def test_sign_test_matches_hand_computed_values():
    assert sign_test_p(0, 0) == 1.0
    assert sign_test_p(1, 1) == 1.0
    assert sign_test_p(0, 5) == 2 / 32  # both-tails probability of a 5-0 split
    assert round(sign_test_p(1, 6), 4) == round(2 * (1 + 7) / 128, 4)


def test_refusal_detector():
    assert is_refusal("I don't know — no relevant documents found.")
    assert is_refusal("The document does not mention a passport number.")
    assert is_refusal("That isn’t provided; I can’t determine it.")
    assert not is_refusal("Maya Chen works in Toronto [1].")


def test_eval_mode_pins_temperature_zero(monkeypatch):
    seen = []
    fake = FakeGroq()
    original = fake._create

    def spy(model, messages, stream=False, **kwargs):
        seen.append(kwargs)
        return original(model, messages, stream=stream, **kwargs)

    fake.chat.completions.create = spy
    monkeypatch.setattr(llm_client, "_client", lambda: fake)
    monkeypatch.setattr(get_settings(), "eval_mode", True)

    llm_client.generate("hello")

    assert seen == [{"temperature": 0}]
