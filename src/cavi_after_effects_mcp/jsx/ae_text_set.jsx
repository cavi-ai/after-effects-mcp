$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), source, doc, i;
    if (!(layer instanceof TextLayer)) {
        caviFail("Layer " + layer.name + " is not a text layer");
    }
    source = layer.property("ADBE Text Properties").property("ADBE Text Document");
    doc = source.value;
    if (a.text !== null) { doc.text = a.text; }
    caviTextStyle(doc, a);
    if (source.numKeys > 0) {
        for (i = 1; i <= source.numKeys; i++) { source.setValueAtKey(i, doc); }
    } else {
        source.setValue(doc);
    }
    doc = source.value;
    caviReport({comp: comp.name, layer: layer.name, text: doc.text, font: doc.font, size: doc.fontSize,
        tracking: doc.tracking, leading: doc.leading, justification: String(doc.justification),
        box: doc.boxText ? doc.boxTextSize : null, fill: doc.applyFill ? doc.fillColor : null,
        stroke: doc.applyStroke ? doc.strokeColor : null,
        animators: layer.property("ADBE Text Properties").property("ADBE Text Animators").numProperties,
        errors: []});
})();
