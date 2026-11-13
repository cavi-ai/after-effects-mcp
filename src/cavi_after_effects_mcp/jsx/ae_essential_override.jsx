$.evalFile(new File(CAVI_LIB));

// Overrides the Essential Properties of a nested comp instance; a string sets source text, anything else is the value.
(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), group, i, names = [], done = [], name, prop, value, doc;
    if (!(layer.source instanceof CompItem)) { caviFail("Layer " + layer.name + " is not a nested comp"); }
    group = layer.essentialProperty;
    for (i = 1; i <= group.numProperties; i++) { names.push(group.property(i).name); }
    for (name in a.values) {
        prop = group.property(name);
        if (!prop) {
            caviFail("Comp " + layer.source.name + " exposes no Essential Property " + name + "; it has: " + names.join(", "));
        }
        value = a.values[name];
        if (prop.propertyValueType === PropertyValueType.TEXT_DOCUMENT) {
            doc = prop.value;
            doc.text = String(value);
            prop.setValue(doc);
        } else {
            prop.setValue(value);
        }
        done.push(name);
    }
    caviReport({comp: comp.name, layer: layer.name, source: layer.source.name, available: names, overridden: done, errors: []});
})();
