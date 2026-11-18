$.evalFile(new File(CAVI_LIB));

// Styles characters [r.start, r.end) of doc; ``where`` names the text for a range past its end.
function styleRange(doc, r, where) {
    var range;
    if (typeof doc.characterRange !== "function") {
        caviFail("This After Effects has no TextDocument.characterRange, so ranges cannot be styled");
    }
    if (r.end > doc.text.length) {
        caviFail("Range " + r.start + "-" + r.end + " is past the end of " + where + " (" + doc.text.length + " characters)");
    }
    range = doc.characterRange(r.start, r.end);
    if (r.font !== null) {
        if (app.fonts.getFontsByPostScriptName(r.font).length === 0) {
            caviFail("Font " + r.font + " is not installed; ae_fonts lists the PostScript names");
        }
        range.font = r.font;
    }
    if (r.size !== null) { range.fontSize = r.size; }
    if (r.fill !== null) { range.applyFill = true; range.fillColor = r.fill; }
    if (r.stroke !== null) { range.applyStroke = true; range.strokeColor = r.stroke; }
    if (r.stroke_width !== null) { range.strokeWidth = r.stroke_width; }
    if (r.tracking !== null) { range.tracking = r.tracking; }
    if (r.bold !== null) { range.fauxBold = r.bold; }
    if (r.italic !== null) { range.fauxItalic = r.italic; }
    if (r.baseline_shift !== null) { range.baselineShift = r.baseline_shift; }
}

// A range's style as it reads back; a value the range's characters do not share is null.
function rangeStyle(doc, r) {
    var range = doc.characterRange(r.start, r.end);
    return {start: r.start, end: r.end, font: range.font, size: range.fontSize, fill: range.applyFill ? range.fillColor : null,
        stroke: range.applyStroke ? range.strokeColor : null, tracking: range.tracking, bold: range.fauxBold,
        italic: range.fauxItalic, baseline_shift: range.baselineShift};
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), source, doc, i, j, ranges = [];
    if (!(layer instanceof TextLayer)) {
        caviFail("Layer " + layer.name + " is not a text layer");
    }
    source = layer.property("ADBE Text Properties").property("ADBE Text Document");
    // Each Source Text key keeps its own text unless text is given; the style applies to every key.
    for (i = source.numKeys > 0 ? 1 : 0; i <= source.numKeys; i++) {
        doc = i > 0 ? source.keyValue(i) : source.value;
        if (a.text !== null) { doc.text = a.text; }
        caviTextStyle(doc, a);
        for (j = 0; j < a.ranges.length; j++) {
            styleRange(doc, a.ranges[j], i > 0 ? "Source Text key " + i : "the text");
        }
        if (i > 0) { source.setValueAtKey(i, doc); } else { source.setValue(doc); }
    }
    doc = source.value;
    for (j = 0; j < a.ranges.length; j++) {
        ranges.push(rangeStyle(doc, a.ranges[j]));
    }
    caviReport({comp: comp.name, layer: layer.name, keys: source.numKeys, text: doc.text, font: doc.font, size: doc.fontSize,
        tracking: doc.tracking, leading: doc.leading, justification: String(doc.justification),
        box: doc.boxText ? doc.boxTextSize : null, fill: doc.applyFill ? doc.fillColor : null,
        stroke: doc.applyStroke ? doc.strokeColor : null, ranges: ranges,
        animators: layer.property("ADBE Text Properties").property("ADBE Text Animators").numProperties,
        errors: []});
})();
