$.evalFile(new File(CAVI_LIB));

function visit(prop, path, layer, out, a) {
    var i, expression, error;
    if (prop.propertyType === PropertyType.PROPERTY) {
        try {
            if (!prop.canSetExpression) { return; }
            expression = prop.expression;
            if (expression === "") { return; }
            error = prop.expressionError;
            out.items.push({layer: layer.name, property: path, expression: expression, enabled: prop.expressionEnabled, error: error === "" ? null : error});
            if (error !== "") { out.broken++; }
            if (error !== "" && a.remove_broken) { prop.expression = ""; out.removed++; }
        } catch (skipped) { return; }
        return;
    }
    for (i = 1; i <= prop.numProperties; i++) {
        try { visit(prop.property(i), path + "/" + prop.property(i).name, layer, out, a); } catch (hidden) { continue; }
    }
}

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), out = {items: [], broken: 0, removed: 0}, i, layer;
    for (i = 1; i <= comp.numLayers; i++) {
        layer = comp.layer(i);
        if (a.layer !== null && layer.index !== caviLayer(comp, a.layer).index) { continue; }
        visit(layer, layer.name, layer, out, a);
    }
    caviReport({comp: comp.name, expressions: out.items, broken: out.broken, removed: out.removed, errors: []});
})();
