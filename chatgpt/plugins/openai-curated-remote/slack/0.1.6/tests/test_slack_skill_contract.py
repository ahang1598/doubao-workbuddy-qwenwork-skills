from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def test_default_triage_resolves_current_user_and_includes_group_dms() -> None:
    skill = (PLUGIN_ROOT / "skills" / "slack" / "SKILL.md").read_text()

    resolution = (
        "Resolve the current user with `slack_read_user_profile` before any search query "
        "containing `<@USER_ID>`"
    )
    assert resolution in skill
    assert skill.index(resolution) < skill.index("from:<@USER_ID>")

    default_scope = skill.split("If no source scope was provided", 1)[1].split(
        "- named channel:", 1
    )[0]
    assert "unanswered direct conversations" in default_scope
    assert "unanswered group DMs" in default_scope
    assert 'channel_types="mpim"' in skill
