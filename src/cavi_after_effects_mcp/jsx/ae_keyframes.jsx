$.evalFile(new File(CAVI_LIB));

(function () {
    var a = CAVI_ARGS, comp = caviComp(a.comp), layer = caviLayer(comp, a.layer), prop = caviProp(layer, a.property), i;
    if (a.replace) {
        for (i = prop.numKeys; i >= 1; i--) {
            prop.removeKey(i);
        }
    }
    if (a.keyframes.length) {
        caviKeys(prop, a.keyframes, a.ease);
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
