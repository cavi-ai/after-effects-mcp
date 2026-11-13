$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), group, props, selector, name, applied = [];
    var match = {opacity: "ADBE Text Opacity", position: "ADBE Text Position 3D", tracking: "ADBE Text Tracking Amount",
        scale: "ADBE Text Scale 3D", blur: "ADBE Text Blur", rotation: "ADBE Text Rotation"};
    var units = {characters: 1, words: 3, lines: 4};
    var value;
    if (!(layer instanceof TextLayer)) {
        caviFail("Layer " + layer.name + " is not a text layer");
    }
    group = layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
    if (a.name) { group.name = a.name; }
    props = group.property("ADBE Text Animator Properties");
    for (name in a.properties) {
        if (a.properties.hasOwnProperty(name) && a.properties[name] !== null) {
            value = a.properties[name];
            if (name === "position" && value.length === 2) { value = [value[0], value[1], 0]; }
            if (name === "scale" && value.length === 2) { value = [value[0], value[1], 100]; }
            props.addProperty(match[name]).setValue(value);
            applied.push(name);
        }
    }
    selector = group.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
    selector.property("ADBE Text Range Advanced").property("ADBE Text Range Type2").setValue(units[a.unit]);
    caviKeys(selector.property("ADBE Text Percent Start"),
        [{time: a.start, value: 0, ease_in: null, ease_out: null, interpolation: null},
         {time: a.start + a.duration, value: 100, ease_in: null, ease_out: null, interpolation: null}], a.ease);
    caviReport({comp: comp.name, layer: layer.name, animator: group.name, unit: a.unit, properties: applied,
        start: a.start, duration: a.duration, errors: []});
})();
