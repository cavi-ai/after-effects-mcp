$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), prop = caviProp(layer, a.property), i;
    if (a.replace) {
        for (i = prop.numKeys; i >= 1; i--) {
            prop.removeKey(i);
        }
    }
    if (a.remove === "all") {
        for (i = prop.numKeys; i >= 1; i--) { prop.removeKey(i); }
    } else if (a.remove !== null) {
        for (i = prop.numKeys; i >= 1; i--) {
            if (prop.keyTime(i) >= a.remove[0] && prop.keyTime(i) <= a.remove[1]) { prop.removeKey(i); }
        }
    }
    if (a.keyframes.length) {
        caviKeys(prop, a.keyframes, a.ease);
    }
    if (a.restyle) {
        caviRestyle(prop, {hold: a.hold, ease: a.keyframes.length ? null : a.ease, spatial: a.spatial, rove: a.rove});
    }
    if (a.expression !== null) {
        prop.expression = a.expression;
        if (a.expression !== "" && prop.expressionError) {
            caviFail("Expression error: " + prop.expressionError);
        }
    }
    caviReport({comp: comp.name, layer: layer.name, property: prop.name, keys: prop.numKeys,
        expression: prop.expression, expression_enabled: prop.expressionEnabled, errors: []});
})();
