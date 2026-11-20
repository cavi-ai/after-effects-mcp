$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), effect, name, applied = [], value;
    caviGuard3D(comp, layer, "an effect");
    effect = layer.property("ADBE Effect Parade").addProperty(a.match_name);
    if (!effect) {
        caviFail("Cannot add effect " + a.match_name);
    }
    if (a.name) { effect.name = a.name; }
    for (name in a.params) {
        if (a.params.hasOwnProperty(name)) {
            value = a.params[name];
            if (caviIsInput(value)) {
                caviSetLayerInput(effect.property(name), value);
            } else {
                effect.property(name).setValue(caviMenuValue(effect.property(name), value));
            }
            applied.push(name);
        }
    }
    caviReport({comp: comp.name, layer: layer.name, effect: {index: effect.propertyIndex, name: effect.name,
        match_name: effect.matchName}, params: applied, errors: []});
})();
