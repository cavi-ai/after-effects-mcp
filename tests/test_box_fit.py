"""Paragraph box fit judged against the text document, under Node."""

import json
import shutil
import subprocess
import unittest

from cavi_after_effects_mcp import host, models


@unittest.skipUnless(shutil.which("node"), "node is required")
class BoxFitTest(unittest.TestCase):
    def setUp(self):
        source = (host.JSX / "lib.jsx").read_text()
        names = ("caviTextStyle", "caviBoxCanGrow", "caviBoxFits", "caviBoxAligns", "caviNameOf", "caviEnum")
        self.functions = ""
        for name in names:
            start = source.index(f"function {name}(")
            self.functions += source[start:source.index("\n}\n", start) + 3]

    def node(self, body, payload):
        script = "function caviFail(message) { throw new Error(message); }\n" + self.functions + body
        out = subprocess.run(["node", "-e", script, json.dumps(payload)], capture_output=True, text=True,
                             check=True)
        return json.loads(out.stdout)

    def apply(self, spec, box_text=True, api=True, alignment="CENTER"):
        """caviTextStyle on a paragraph document whose boxVerticalAlignment is ``alignment``."""
        body = (
            "const [spec, boxText, api, alignment] = JSON.parse(process.argv[1]);\n"
            "var BoxVerticalAlignment = {TOP: 'TOP', CENTER: 'CENTER', BOTTOM: 'BOTTOM', JUSTIFY: 'JUSTIFY'};\n"
            "var BoxAutoFitPolicy = api ? {NONE: 'NONE', HEIGHT_CURSOR: 'HEIGHT_CURSOR',\n"
            "  HEIGHT_PRECISE_BOUNDS: 'HEIGHT_PRECISE_BOUNDS', HEIGHT_BASELINE: 'HEIGHT_BASELINE'} : undefined;\n"
            "const doc = {boxText: boxText, boxVerticalAlignment: BoxVerticalAlignment[alignment],\n"
            "  boxAutoFitPolicy: api ? BoxAutoFitPolicy.NONE : undefined, boxInsetSpacing: 0};\n"
            "let out;\n"
            "try { caviTextStyle(doc, spec); out = {boxAutoFitPolicy: doc.boxAutoFitPolicy}; }\n"
            "catch (error) { out = {error: error.message}; }\n"
            "process.stdout.write(JSON.stringify(out));")
        return self.node(body, [spec, box_text, api, alignment])

    def can_grow(self, fit, align):
        body = ("const [fit, align] = JSON.parse(process.argv[1]);\n"
                "process.stdout.write(JSON.stringify(caviBoxCanGrow(fit, align)));")
        return self.node(body, [fit, align])

    def test_an_omitted_align_on_a_centered_box_names_that_alignment(self):
        self.assertEqual(self.apply({"box_fit": "cursor"}), {
            "error": "box_fit grows a box only with box_align top; the text is aligned center"})

    def test_top_alignment_sets_the_cursor_fit(self):
        self.assertEqual(self.apply({"box_align": "top", "box_fit": "cursor"}),
                         {"boxAutoFitPolicy": "HEIGHT_CURSOR"})

    def test_point_text_is_refused(self):
        self.assertEqual(self.apply({"box_fit": "cursor"}, box_text=False), {
            "error": "box_fit, box_align and box_inset apply to paragraph text; this layer is point text"})

    def test_a_missing_box_auto_fit_policy_needs_24_6(self):
        self.assertEqual(self.apply({"box_fit": "cursor"}, api=False), {
            "error": "box_fit, box_align and box_inset need After Effects 24.6 or later"})

    def test_the_argument_gate_allows_a_missing_align_the_document_rule_refuses(self):
        matrix = (("none", "center", True), ("cursor", "top", True), ("cursor", "center", False))
        for fit, align, allowed in matrix:
            with self.subTest(fit=fit, align=align):
                self.assertEqual(self.can_grow(fit, align), allowed)
                if allowed:
                    models.box_fit_check(fit, align)
                else:
                    message = f"^box_fit grows a box only with box_align top, not {align}$"
                    with self.assertRaisesRegex(ValueError, message):
                        models.box_fit_check(fit, align)
        models.box_fit_check("cursor", None)
        self.assertFalse(self.can_grow("cursor", None))
