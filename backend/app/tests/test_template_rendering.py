"""Tests for Jinja2 template rendering — capitolato/base.j2.

Verifies that enriched_requirements dict values are accessed directly
(no double nesting via .get("enriched_requirements", {})).
"""

from pathlib import Path

import jinja2
import pytest

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "capitolato"


@pytest.fixture()
def env() -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        keep_trailing_newline=True,
    )


@pytest.fixture()
def base_template(env: jinja2.Environment) -> jinja2.Template:
    return env.get_template("base.j2")


# ---- helpers -----------------------------------------------------------


def _make_data(*, title: str = "Test ERP", fr_count: int = 0) -> dict:
    """Build a minimal enriched_requirements dict (flat, no double nesting)."""
    frs = [
        {
            "id": f"FR-{i + 1:03d}",
            "title": f"Req {i + 1}",
            "description": f"Desc {i + 1}",
            "priority": "High",
        }
        for i in range(fr_count)
    ]
    return {
        "project": {
            "title": title,
            "organization": "ACME",
            "reference_code": "PRJ-001",
            "description": "A test project",
        },
        "scope": {"objectives": ["Obj 1"], "in_scope": ["Item A"], "out_of_scope": ["Item B"]},
        "functional_requirements": frs,
        "technical_requirements": [],
        "sla": {"K1": "99%", "K2": "1%", "K3": "0"},
        "security_compliance": {"standards": ["ISO 27001"]},
        "integrations": [],
        "timeline": {"go_live": "2027-01-01"},
        "budget": {"model": "T&M"},
        "regulatory_references": [],
        "evaluation_criteria": [],
    }


# ---- tests -------------------------------------------------------------


class TestCapitolatoTemplateRendering:
    """Suite: base.j2 renders correctly from a flat enriched_requirements dict."""

    def test_capitolato_template_renders_title(self, base_template: jinja2.Template) -> None:
        """Project title should appear in the rendered output, not TBD/empty."""
        data = _make_data(title="Test ERP")
        output = base_template.render(enriched_requirements=data)
        assert "Test ERP" in output

    def test_capitolato_template_renders_functional_reqs_table(
        self, base_template: jinja2.Template
    ) -> None:
        """A markdown table with all FR rows should appear."""
        data = _make_data(fr_count=3)
        output = base_template.render(enriched_requirements=data)
        for i in range(1, 4):
            assert f"FR-{i:03d}" in output, f"FR-{i:03d} missing from rendered output"
        # Table header row must be present
        assert "| ID |" in output

    def test_template_no_double_nesting(self, base_template: jinja2.Template) -> None:
        """Passing project.title at top level must NOT produce empty/TBD title."""
        data = _make_data(title="Unique Project X")
        output = base_template.render(enriched_requirements=data)
        # Title should appear; the fallback "CAPITOLATO DI GARA" must NOT appear
        # when a title is explicitly provided
        assert "Unique Project X" in output
        assert "CAPITOLATO DI GARA" not in output
